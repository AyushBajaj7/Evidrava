"""Candidate-frame checks and a deterministic, group-preserving sample draw.

This module intentionally prepares a future study draw without interpreting
eligibility evidence.  A real draw is accepted only when a separately frozen
protocol binds the exact bytes of the candidate frame.
"""
from collections import Counter, defaultdict
import csv
from datetime import datetime
from hashlib import sha256
from io import StringIO
import json
import re
from pathlib import Path


FRAME_FIELDS = ["matter_id", "related_matter_group", "eligibility_status", "eligibility_reason"]
ALLOWED_STATUSES = {"eligible", "excluded", "pending"}
ALGORITHM = "evidrava-group-draw-v1"
MAX_FRAME_BYTES = 2_000_000
MAX_TARGET_MATTERS = 10_000
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def canonical_json(value):
    """Encode a reproducibility object without locale-dependent formatting."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_frame(path):
    """Read a small, explicit candidate frame without silently normalizing it."""
    path = Path(path)
    blob = path.read_bytes()
    if len(blob) > MAX_FRAME_BYTES:
        raise ValueError("Candidate frame exceeds the 2 MB pilot limit")
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Candidate frame must be UTF-8 CSV") from exc
    rows = list(csv.DictReader(StringIO(text, newline="")))
    if not rows and not text.strip():
        raise ValueError("Candidate frame is empty")
    header = next(csv.reader(StringIO(text, newline="")), [])
    if header != FRAME_FIELDS:
        raise ValueError("Candidate frame requires exactly these columns in order: " + ", ".join(FRAME_FIELDS))
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("A candidate-frame row has the wrong number of columns")
    return rows, sha256(blob).hexdigest()


def _diagnostic(code, row, field, message, matter_id=None):
    return {"severity": "error", "code": code, "row": row, "field": field,
            "matter_id": matter_id, "message": message}


def inspect_frame(path):
    """Return a diagnostic report for a candidate frame; never select records."""
    rows, frame_sha256 = read_frame(path)
    diagnostics = []
    ids = [row["matter_id"].strip() for row in rows]
    id_counts = Counter(ids)
    normalized = []

    for index, row in enumerate(rows, start=2):
        matter_id = row["matter_id"].strip()
        group = row["related_matter_group"].strip()
        status = row["eligibility_status"].strip().lower()
        reason = row["eligibility_reason"].strip()
        if not matter_id:
            diagnostics.append(_diagnostic("MATTER_ID_MISSING", index, "matter_id", "Every frame row requires a matter ID"))
        elif row["matter_id"] != matter_id or not SAFE_ID.fullmatch(matter_id):
            diagnostics.append(_diagnostic("MATTER_ID_INVALID", index, "matter_id", "Use a canonical safe matter ID", matter_id))
        elif id_counts[matter_id] > 1:
            diagnostics.append(_diagnostic("DUPLICATE_MATTER_ID", index, "matter_id", "A matter can occur only once in the candidate frame", matter_id))
        if status not in ALLOWED_STATUSES:
            diagnostics.append(_diagnostic("ELIGIBILITY_STATUS_INVALID", index, "eligibility_status", "Use eligible, excluded or pending", matter_id or None))
        if not reason:
            diagnostics.append(_diagnostic("ELIGIBILITY_REASON_MISSING", index, "eligibility_reason", "State why this candidate has its current status", matter_id or None))
        if status == "eligible" and not group:
            diagnostics.append(_diagnostic("GROUP_MISSING", index, "related_matter_group", "An eligible matter needs a declared related-matter group", matter_id or None))
        elif group and (row["related_matter_group"] != group or not SAFE_ID.fullmatch(group)):
            diagnostics.append(_diagnostic("GROUP_INVALID", index, "related_matter_group", "Use a canonical safe group ID or leave it blank for a noneligible candidate", matter_id or None))
        normalized.append({"matter_id": matter_id, "related_matter_group": group, "eligibility_status": status,
                           "eligibility_reason": reason, "row": index})

    valid_eligible = [row for row in normalized if row["eligibility_status"] == "eligible" and row["matter_id"]
                      and SAFE_ID.fullmatch(row["matter_id"]) and row["related_matter_group"]
                      and SAFE_ID.fullmatch(row["related_matter_group"]) and id_counts[row["matter_id"]] == 1]
    if not valid_eligible:
        diagnostics.append(_diagnostic("NO_ELIGIBLE_MATTERS", None, "eligibility_status", "At least one eligible matter is needed before a frame can be frozen"))

    groups = defaultdict(list)
    for row in valid_eligible:
        groups[row["related_matter_group"]].append(row["matter_id"])
    group_members = {group: sorted(members) for group, members in sorted(groups.items())}
    counts = Counter(row["eligibility_status"] for row in normalized)
    status = "INVALID" if diagnostics else "READY_TO_FREEZE"
    return {
        "report_kind": "candidate-frame-check",
        "status": status,
        "research_decision": "NOT_EVALUATED",
        "frame_name": Path(path).name,
        "frame_sha256": frame_sha256,
        "frame_schema": {"columns": FRAME_FIELDS, "max_bytes": MAX_FRAME_BYTES},
        "summary": {
            "candidate_matters": len(rows),
            "eligible_matters": counts["eligible"],
            "excluded_matters": counts["excluded"],
            "pending_matters": counts["pending"],
            "eligible_related_matter_groups": len(group_members)
        },
        "eligible_groups": group_members,
        "diagnostics": sorted(diagnostics, key=lambda d: (d["row"] is None, d["row"] or 0, d["code"], d["field"])),
        "limitations": [
            "This check does not verify a stated eligibility reason, source, public date, market coverage or audit.",
            "Pending and excluded matters are retained in the frame but cannot be selected.",
            "A draw requires a separately frozen protocol whose frame_sha256 matches these exact frame bytes.",
            "A deterministic draw prepares a sample; it does not make the research decision evaluable."
        ]
    }


def _load_protocol(path):
    """Read a narrow frozen-protocol contract and reject ambiguous JSON keys."""
    path = Path(path)
    blob = path.read_bytes()

    def no_duplicates(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Frozen protocol repeats JSON key: {key}")
            value[key] = item
        return value

    try:
        protocol = json.loads(blob.decode("utf-8-sig"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Frozen protocol must be valid UTF-8 JSON") from exc
    if not isinstance(protocol, dict):
        raise ValueError("Frozen protocol must be a JSON object")
    required = {"protocol_id", "state", "frozen_at", "frame_sha256", "sampling"}
    missing = sorted(required - set(protocol))
    if missing:
        raise ValueError("Frozen protocol is missing: " + ", ".join(missing))
    if not isinstance(protocol["protocol_id"], str) or not SAFE_ID.fullmatch(protocol["protocol_id"]):
        raise ValueError("Frozen protocol requires a safe protocol_id")
    if protocol["state"] != "FROZEN":
        raise ValueError("Protocol must be explicitly FROZEN before drawing a sample")
    if not isinstance(protocol["frozen_at"], str):
        raise ValueError("Frozen protocol requires an RFC3339 frozen_at timestamp")
    try:
        frozen_at = datetime.fromisoformat(protocol["frozen_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Frozen protocol requires an RFC3339 frozen_at timestamp") from exc
    if frozen_at.tzinfo is None:
        raise ValueError("Frozen protocol frozen_at must include a timezone")
    frame_sha256 = protocol["frame_sha256"]
    if not isinstance(frame_sha256, str) or not SHA256.fullmatch(frame_sha256):
        raise ValueError("Frozen protocol requires a lowercase SHA-256 frame_sha256")
    sampling = protocol["sampling"]
    if not isinstance(sampling, dict):
        raise ValueError("Frozen protocol requires a sampling object")
    required_sampling = {"algorithm", "seed", "target_matters", "replacement_policy"}
    missing_sampling = sorted(required_sampling - set(sampling))
    if missing_sampling:
        raise ValueError("Frozen protocol sampling is missing: " + ", ".join(missing_sampling))
    if sampling["algorithm"] != ALGORITHM:
        raise ValueError(f"Frozen protocol sampling algorithm must be {ALGORITHM}")
    if isinstance(sampling["seed"], bool) or not isinstance(sampling["seed"], int):
        raise ValueError("Frozen protocol sampling seed must be an integer")
    if isinstance(sampling["target_matters"], bool) or not isinstance(sampling["target_matters"], int) or not 1 <= sampling["target_matters"] <= MAX_TARGET_MATTERS:
        raise ValueError(f"Frozen protocol target_matters must be an integer from 1 to {MAX_TARGET_MATTERS}")
    if sampling["replacement_policy"] != "none":
        raise ValueError("Frozen protocol replacement_policy must be none for this pilot draw")
    return protocol, sha256(blob).hexdigest()


def _ranked_groups(groups, seed):
    def rank(group_id):
        payload = f"{ALGORITHM}\0{seed}\0{group_id}".encode("utf-8")
        return sha256(payload).hexdigest()
    return sorted(groups.items(), key=lambda item: (rank(item[0]), item[0]))


def _select_groups(groups, target_matters, seed):
    """Choose a deterministic exact subset without splitting a related group."""
    ranked = _ranked_groups(groups, seed)
    paths = {0: ()}
    for group_id, members in ranked:
        size = len(members)
        for subtotal in sorted(tuple(paths), reverse=True):
            total = subtotal + size
            if total <= target_matters and total not in paths:
                paths[total] = paths[subtotal] + (group_id,)
    if target_matters not in paths:
        available = sum(len(members) for members in groups.values())
        raise ValueError(f"TARGET_NOT_REACHABLE: target_matters={target_matters}; eligible_matters={available}; no whole-group selection reaches the target")
    selected = paths[target_matters]
    return selected, [group_id for group_id, _ in ranked]


def draw_sample(frame_path, protocol_path):
    """Produce a deterministic selection manifest from a frozen protocol and exact frame."""
    frame = inspect_frame(frame_path)
    if frame["status"] != "READY_TO_FREEZE":
        raise ValueError("Candidate frame is invalid; resolve diagnostics before drawing a sample")
    protocol, protocol_sha256 = _load_protocol(protocol_path)
    if protocol["frame_sha256"] != frame["frame_sha256"]:
        raise ValueError("FROZEN_INPUT_CHANGED: protocol frame_sha256 does not match the supplied candidate frame")
    sampling = protocol["sampling"]
    selected_groups, ranked_groups = _select_groups(frame["eligible_groups"], sampling["target_matters"], sampling["seed"])
    selected_set = set(selected_groups)
    selected_matter_ids = sorted(matter_id for group_id, members in frame["eligible_groups"].items()
                                if group_id in selected_set for matter_id in members)
    selection = {
        "kind": "evidrava-selection-manifest",
        "manifest_version": 1,
        "publication": "local_only",
        "research_decision": "NOT_EVALUATED",
        "selection_algorithm": ALGORITHM,
        "seed": sampling["seed"],
        "target_matters": sampling["target_matters"],
        "replacement_policy": sampling["replacement_policy"],
        "protocol": {"protocol_id": protocol["protocol_id"], "frozen_at": protocol["frozen_at"], "sha256": protocol_sha256},
        "frame_sha256": frame["frame_sha256"],
        "selected_matter_ids": selected_matter_ids,
        "selected_group_ids": list(selected_groups),
        "group_rank_order": ranked_groups,
        "limitations": [
            "Selection is group-preserving and exact for the declared target; it does not verify the frame's eligibility statements.",
            "No replacement has been drawn. Any amendment requires a new frozen protocol and manifest.",
            "Selection does not provide source verification, audit credit, market-data coverage or a research decision."
        ]
    }
    selection_blob = (canonical_json(selection) + "\n").encode("utf-8")
    report = {
        "report_kind": "candidate-frame-draw",
        "status": "DRAWN",
        "research_decision": "NOT_EVALUATED",
        "frame_name": frame["frame_name"],
        "frame_sha256": frame["frame_sha256"],
        "protocol_sha256": protocol_sha256,
        "selection_manifest_sha256": sha256(selection_blob).hexdigest(),
        "summary": {
            **frame["summary"],
            "target_matters": sampling["target_matters"],
            "selected_matters": len(selected_matter_ids),
            "selected_related_matter_groups": len(selected_groups)
        },
        "selected_matter_ids": selected_matter_ids,
        "selected_group_ids": list(selected_groups),
        "diagnostics": [],
        "limitations": selection["limitations"]
    }
    return report, selection_blob
