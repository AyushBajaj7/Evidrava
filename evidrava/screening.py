"""Offline preparation and workload summaries for the fixed reconnaissance batch."""
from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
import json
import math
from pathlib import Path
from statistics import mean, median

FIXED_FIELDS = ["screening_id", "listing_date_stratum", "page_index_zero_based", "row_in_page_one_based",
                "listing_record_position", "listing_date", "title", "url", "official_listing_id",
                "response_sha256", "machine_title_triage", "machine_title_reason"]
HUMAN_FIELDS = ["human_reviewer_id", "human_screening_decision", "human_decision_reason", "document_opened",
                "eligibility_source_locator", "cash_equity_scope", "group_key_or_uncertain", "predecessor_search_status",
                "predecessor_evidence", "screening_active_minutes", "grouping_active_minutes",
                "predecessor_active_minutes", "access_wait_minutes", "followup_needed", "notes"]
FIELDS = FIXED_FIELDS + HUMAN_FIELDS
ACTIVE_FIELDS = ["screening_active_minutes", "grouping_active_minutes", "predecessor_active_minutes"]
TIME_FIELDS = ACTIVE_FIELDS + ["access_wait_minutes"]
REFERENCE_SHA256 = "2379c6b8d1b0aa25e81244744463c3d711b9bdca43c9f9563b2055fb88b4f770"


def finite_total(values):
    total = sum(values)
    if not math.isfinite(total):
        raise ValueError("Combined screening minutes exceed the finite numeric range; correct the entered timings")
    return total


def read_csv(path):
    blob = Path(path).read_bytes()
    if len(blob) > 2_000_000:
        raise ValueError("Screening CSV exceeds the 2 MB reconnaissance limit")
    reader = csv.DictReader(StringIO(blob.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != FIELDS:
        raise ValueError("Screening CSV requires the original 27 columns in their original order; duplicate/missing/extra headers are not accepted")
    rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("A screening CSV row has the wrong number of fields")
    return rows, sha256(blob).hexdigest()


def load_reference(path):
    """Validate preserved bytes and captures without executing the old preparer."""
    path = Path(path).resolve()
    rows, digest = read_csv(path)
    base = path.parent
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if digest != REFERENCE_SHA256 or digest != manifest.get("screening_csv_initial_sha256"):
        raise ValueError("Original screening reference changed. Restore its preserved bytes and put human entries in a separate working copy")
    if len(rows) != 30 or len({r["screening_id"] for r in rows}) != 30:
        raise ValueError("Reference must contain the original 30 distinct records")
    preparer = base.parent.parent / "scripts" / "prepare_screening_batch.py"
    if sha256(preparer.read_bytes()).hexdigest() != manifest.get("script_sha256"):
        raise ValueError("Preparer fingerprint differs from the recorded batch; review the change before using this reference")
    requests = manifest.get("requests", [])
    if len(requests) != 9:
        raise ValueError("Reference manifest must describe the nine captured requests")
    seen = set()
    for request in requests:
        raw = (base / request["raw_path"]).resolve()
        meta = (base / request["request_path"]).resolve()
        if not raw.is_relative_to(base) or not meta.is_relative_to(base):
            raise ValueError("Capture path escapes the original screening directory")
        if raw in seen:
            raise ValueError("Duplicate raw capture in reference manifest")
        seen.add(raw)
        raw_digest = sha256(raw.read_bytes()).hexdigest()
        metadata = json.loads(meta.read_text(encoding="utf-8"))
        if raw_digest != request["sha256"] or raw_digest != metadata.get("sha256") or metadata.get("parameters") != request["parameters"]:
            raise ValueError(f"Capture bytes or request parameters changed: {raw.name}")
    if {r["response_sha256"] for r in rows} != {r["sha256"] for r in requests}:
        raise ValueError("Reference records and capture hashes do not agree")
    return rows, {"reference_sha256": digest, "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
                  "preparer_sha256": manifest["script_sha256"], "verified_raw_captures": len(seen)}


def summarize_screening(rows, reference, candidate_listings=None):
    """Summarize human-entered observations; never generate decisions or timings."""
    if candidate_listings is not None and (isinstance(candidate_listings, bool) or not isinstance(candidate_listings, int) or candidate_listings <= 0):
        raise ValueError("Candidate listing count must be a positive integer")
    expected = {r["screening_id"]: r for r in reference}
    if len(expected) != len(reference) or not expected or "" in expected:
        raise ValueError("Reference identifiers must be nonempty and unique")
    diagnostics, records = [], []

    def emit(code, sid, field, message):
        diagnostics.append({"severity": "error", "code": code, "screening_id": sid, "field": field, "message": message})

    id_counts = Counter(r["screening_id"] for r in rows)
    for sid, count in sorted(id_counts.items()):
        if not sid:
            emit("ID_MISSING", sid, "screening_id", "Every batch row requires its original ID")
        elif sid not in expected:
            emit("UNKNOWN_ID", sid, "screening_id", "Record is not in the fixed reconnaissance batch")
        if count > 1:
            emit("DUPLICATE_ID", sid, "screening_id", "Duplicated record cannot contribute workload statistics")
    for sid in sorted(set(expected) - set(id_counts)):
        emit("RECORD_MISSING", sid, "screening_id", "Record was removed; all selected records remain in completion accounting")

    for r in rows:
        sid = r["screening_id"]
        if sid not in expected or id_counts[sid] != 1:
            continue
        before = len(diagnostics)
        for field in FIXED_FIELDS:
            if r[field] != expected[sid][field]:
                emit("METADATA_CHANGED", sid, field, "Keep the original listing metadata and machine triage unchanged")
        text = {k: r[k].strip() for k in HUMAN_FIELDS}
        decision = text["human_screening_decision"].lower()
        decision = {"included": "include", "excluded": "exclude"}.get(decision, decision)
        if decision and decision not in {"include", "exclude", "uncertain"}:
            emit("DECISION_INVALID", sid, "human_screening_decision", "Use include, exclude or uncertain")
        for field, allowed in [("document_opened", {"yes", "no"}), ("cash_equity_scope", {"yes", "no", "uncertain"}),
                               ("followup_needed", {"yes", "no"}), ("predecessor_search_status", {"not_started", "in_progress", "complete", "not_applicable", "uncertain"})]:
            if text[field] and text[field].lower() not in allowed:
                emit("VALUE_INVALID", sid, field, f"Allowed values: {', '.join(sorted(allowed))}")
        times = {}
        for field in TIME_FIELDS:
            times[field] = None
            if text[field]:
                try:
                    value = float(text[field])
                    if not math.isfinite(value) or value < 0:
                        raise ValueError()
                    times[field] = value
                except (ValueError, OverflowError):
                    emit("TIME_INVALID", sid, field, "Enter finite nonnegative minutes; blank means unmeasured, zero means observed zero")
        opened = text["document_opened"].lower()
        cash_scope = text["cash_equity_scope"].lower()
        pred = text["predecessor_search_status"].lower()
        follow = text["followup_needed"].lower()
        # Incomplete entries are ordinary work in progress. Explicitly
        # contradictory completed claims are errors.
        if decision in {"include", "exclude"} and opened == "no":
            emit("UNSUPPORTED_DECISION", sid, "document_opened", "Use uncertain until the source needed for this disposition has been reviewed")
        if decision == "include" and cash_scope in {"no", "uncertain"}:
            emit("SCOPE_CONFLICT", sid, "cash_equity_scope", "An inclusion disposition requires cash-equity scope to be established")
        unresolved = decision == "uncertain" or follow == "yes" or (bool(decision) and (pred in {"not_started", "in_progress", "uncertain"} or text["group_key_or_uncertain"].lower() == "uncertain"))
        if unresolved and follow == "no":
            emit("FOLLOWUP_CONFLICT", sid, "followup_needed", "Uncertain decisions or unfinished grouping/predecessor work require follow-up")
        required = ["human_reviewer_id", "human_decision_reason", "document_opened", "cash_equity_scope",
                    "group_key_or_uncertain", "predecessor_search_status", "followup_needed"]
        missing = [f for f in required if not text[f]]
        if decision in {"include", "exclude"} and not text["eligibility_source_locator"]:
            missing.append("eligibility_source_locator")
        if pred == "complete" and not text["predecessor_evidence"]:
            missing.append("predecessor_evidence")
        if not decision:
            missing.append("human_screening_decision")
        valid = len(diagnostics) == before
        disposition_complete = valid and decision in {"include", "exclude", "uncertain"} and not missing
        timing_complete = disposition_complete and all(times[f] is not None for f in ACTIVE_FIELDS)
        records.append({"screening_id": sid, "stratum": expected[sid]["listing_date_stratum"],
                        "title": expected[sid]["title"], "url": expected[sid]["url"], "decision": decision or None,
                        "disposition_complete": disposition_complete, "timing_complete": timing_complete,
                        "unresolved": unresolved, "valid": valid, "missing_fields": sorted(set(missing)),
                        "timings": times, "active_total_minutes": finite_total(times[f] for f in ACTIVE_FIELDS) if timing_complete else None})

    def summary(group, count):
        valid = [r for r in group if r["valid"]]
        completed = [r for r in valid if r["disposition_complete"]]
        timed = [r["active_total_minutes"] for r in valid if r["timing_complete"]]
        measured = {f: [r["timings"][f] for r in valid if r["timings"][f] is not None] for f in TIME_FIELDS}
        active_logged = [v for f in ACTIVE_FIELDS for v in measured[f]]
        return {"expected_records": count, "completed_screening_attempts": len(completed), "pending_records": count - len(completed),
                "decisions": {d: sum(r["decision"] == d for r in completed) for d in ["include", "exclude", "uncertain"]},
                "unresolved_records": sum(r["unresolved"] for r in valid), "complete_timing_observations": len(timed),
                "observed_minutes": {f: {"observations": len(v), "total": finite_total(v) if v else None} for f, v in measured.items()},
                "logged_active_minutes": finite_total(active_logged) if active_logged else None,
                "complete_active_minutes": {"observations": len(timed), "sum": finite_total(timed) if timed else None,
                                            "mean": mean(timed) if timed else None, "median": median(timed) if timed else None,
                                            "min": min(timed) if timed else None, "max": max(timed) if timed else None}}

    strata = {s: summary([r for r in records if r["stratum"] == s], sum(r["listing_date_stratum"] == s for r in reference))
              for s in sorted({r["listing_date_stratum"] for r in reference})}
    total = summary(records, len(reference))
    status = "INVALID" if diagnostics else ("READY_FOR_SCOPE_REVIEW" if total["complete_timing_observations"] == len(reference) else "IN_PROGRESS")
    estimate = {"requested_candidate_listings": candidate_listings, "illustrative_initial_screening_hours": None,
                "assumptions": ["Same listing mix and initial-screening effort as this positional batch",
                                "Excludes future follow-up, annotation, audit and data-linkage work",
                                "A planning scenario, not a population estimate or deadline forecast"]}
    if candidate_listings is not None:
        if status == "READY_FOR_SCOPE_REVIEW":
            try:
                hours = candidate_listings * (total["complete_active_minutes"]["mean"] / 60)
            except OverflowError:
                raise ValueError("Candidate workload exceeds the finite numeric range") from None
            if not math.isfinite(hours):
                raise ValueError("Candidate workload exceeds the finite numeric range")
            estimate["illustrative_initial_screening_hours"] = hours
        else:
            estimate["withheld_reason"] = "All original records need valid, complete timing observations before extrapolating their initial-screening workload"
    return {"report_kind": "screening-workload", "status": status, "research_decision": "NOT_EVALUATED", "summary": total,
            "strata": strata, "records": sorted(records, key=lambda r: r["screening_id"]), "diagnostics": diagnostics,
            "missing_records": sorted(set(expected) - set(id_counts)), "planning_scenario": estimate,
            "limitations": ["Positional reconnaissance batch; not the random research sample",
                            "Human-entered decisions and minutes are recorded assertions, not independently audited facts",
                            "Missing minutes are unavailable; explicit zero is an observed value",
                            "Machine retrieval time and title triage do not count as human work",
                            "Unresolved follow-ups remain open even when the screening attempt is fully timed"]}
