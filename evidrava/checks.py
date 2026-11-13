"""Bounded input checks, independent of Excel's calculated or cached values.

This module diagnoses preparation problems. It never certifies source contents,
market coverage, reviewer identity, model performance, or a research PASS.
"""
from collections import Counter, defaultdict
from datetime import date, datetime
from statistics import median

FIELDS = {"conduct_start", "conduct_end", "alleged_scheme", "instrument", "isin", "legal_status", "order_date"}
VERSION_FIELDS = {"conduct_start": "D", "conduct_end": "E", "alleged_scheme": "F"}
EPISODE_FIELDS = {"instrument": "C", "isin": "D"}


def clean(value):
    return str(value).strip() if value is not None else ""


def key(value):
    return clean(value).casefold()


def day(value):
    if isinstance(value, datetime):
        return value.date() if value.time().isoformat() == "00:00:00" else None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def whole(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 and value == int(value)


def inspect_registry(data):
    diagnostics = list(data.get("loader_diagnostics", []))
    tables = data.get("tables", {})
    rules = data.get("rules", {})
    readiness = []

    def emit(severity, code, sheet, row, col, message):
        diagnostics.append(dict(severity=severity, code=code, sheet=sheet, cell=f"{col}{row}", message=message))

    def error(code, sheet, row, col, message):
        emit("error", code, sheet, row, col, message)

    def warning(code, sheet, row, col, message):
        emit("warning", code, sheet, row, col, message)

    # Invalid colliding IDs cannot be used to approve a related claim.
    indexes = {}
    for sheet in ["People", "Matters", "Orders", "Episodes", "Versions", "Evidence", "SelectionLog"]:
        grouped = defaultdict(list)
        for record in tables.get(sheet, []):
            row, values = record["row"], record["values"]
            if not any(v is not None and v != "" for v in values.values()):
                continue
            ident = key(values.get("A"))
            if not ident:
                error("ID_MISSING", sheet, row, "A", "Populated row requires a nonblank identifier")
                continue
            if str(values.get("A")) != clean(values.get("A")):
                error("ID_WHITESPACE", sheet, row, "A", "Remove surrounding whitespace from the identifier")
            grouped[ident].append(record)
        indexes[sheet] = {}
        for ident, records in grouped.items():
            if len(records) != 1:
                for record in records:
                    error("DUPLICATE_ID", sheet, record["row"], "A", "Identifier must be unique in this table")
            else:
                indexes[sheet][ident] = records[0]

    people, matters, orders, episodes, versions = (indexes[s] for s in ["People", "Matters", "Orders", "Episodes", "Versions"])
    scoped = {k: v for k, v in matters.items() if key(v["values"].get("E")) != "excluded after review"}
    cutoff = day(rules.get("B7"))
    frozen = day(rules.get("B5"))
    if rules.get("B5") not in (None, "") and frozen is None:
        error("FREEZE_DATE_INVALID", "Rules", 5, "B", "Freeze date must be a date-only value")
    if cutoff is None:
        (error if frozen or rules.get("B7") not in (None, "") else warning)(
            "CUTOFF_MISSING", "Rules", 7, "B", "Set a valid date-only collection cutoff before freeze")
    if not frozen:
        readiness.append("Protocol remains DRAFT; screening, software work and provisional extraction may continue")
    if clean(rules.get("B18")) != "All versions":
        error("AUDIT_SCOPE", "Rules", 18, "B", "The accepted pilot requires All versions")
    if key(rules.get("B19")) != "yes":
        error("AUDITOR_POLICY", "Rules", 19, "B", "The accepted pilot requires independent auditors")
    if rules.get("B17") != 1:
        error("AVAILABILITY_LAG", "Rules", 17, "B", "The accepted date-only pilot uses a one-calendar-day lag")
    for coord in ["B8", "B9", "B10", "B12", "B13", "B14", "B15", "B16"]:
        if not whole(rules.get(coord)):
            error("RULE_INVALID", "Rules", int(coord[1:]), "B", "A positive whole-number planning value is required")
    share = rules.get("B11")
    if isinstance(share, bool) or not isinstance(share, (int, float)) or not 0 < share <= 1:
        error("RULE_INVALID", "Rules", 11, "B", "Required audit share must be greater than zero and at most one")
    if not any(key(r["values"].get("C")) == "yes" for r in people.values()):
        readiness.append("Independent reviewer is not registered; this does not block engineering or provisional annotation")
    for ident, record in people.items():
        if key(record["values"].get("C")) not in {"yes", "no"}:
            warning("REVIEWER_INDEPENDENCE_UNKNOWN", "People", record["row"], "C", "Record the real reviewer's independence")

    valid_orders = set()
    for ident, record in orders.items():
        v, row = record["values"], record["row"]
        good = True
        if key(v.get("B")) not in matters:
            error("UNKNOWN_MATTER", "Orders", row, "B", "Order must refer to one unique matter"); good = False
        if not whole(v.get("H")):
            error("ORDER_PAGE_COUNT", "Orders", row, "H", "Known positive whole-number page count required"); good = False
        public = day(v.get("E"))
        if public is None:
            error("PUBLIC_DATE_INVALID", "Orders", row, "E", "Public date must be a date-only value"); good = False
        elif day(v.get("D")) and public < day(v["D"]):
            error("PUBLIC_BEFORE_ORDER", "Orders", row, "E", "Publication cannot precede the order date"); good = False
        if cutoff and public and public > cutoff:
            error("AFTER_CUTOFF", "Orders", row, "E", "This release-scoped workbook contains a post-cutoff order"); good = False
        if key(v.get("F")) not in {"stated on sebi website", "other verified source"}:
            warning("PUBLIC_DATE_UNVERIFIED", "Orders", row, "F", "Assumed availability cannot support strict historical replay")
        if good:
            valid_orders.add(ident)

    included = defaultdict(list)
    for record in tables.get("SelectionLog", []):
        v, row = record["values"], record["row"]
        decision = key(v.get("F"))
        if not decision:
            error("SELECTION_DECISION_MISSING", "SelectionLog", row, "F", "Every populated selection record needs a decision")
        elif decision == "included":
            matter = key(v.get("H"))
            if matter not in matters:
                error("SELECTION_UNKNOWN_MATTER", "SelectionLog", row, "H", "Included matter is absent or duplicated in Matters")
            included[matter].append(row)
        elif decision == "excluded":
            if not clean(v.get("G")):
                error("EXCLUSION_REASON_MISSING", "SelectionLog", row, "G", "Document the exclusion reason")
        else:
            error("SELECTION_DECISION_INVALID", "SelectionLog", row, "F", "Use Included or Excluded")
    for ident, rows in included.items():
        if len(rows) > 1:
            for row in rows:
                error("DUPLICATE_INCLUDED_MATTER", "SelectionLog", row, "H", "Keep exactly one Included record per selected matter")
    for ident, record in scoped.items():
        if ident not in included:
            error("SELECTION_ENTRY_MISSING", "Matters", record["row"], "A", "In-scope matter has no Included selection record")
        if key(record["values"].get("J")) != "yes":
            readiness.append(f"Episode inventory is unfinished for matter {record['values']['A']}")

    scoped_episodes = {}
    for ident, record in episodes.items():
        v, row = record["values"], record["row"]
        if key(v.get("B")) not in matters:
            error("UNKNOWN_MATTER", "Episodes", row, "B", "Episode must refer to one unique matter")
        elif key(v.get("B")) in scoped:
            scoped_episodes[ident] = record
        if clean(v.get("D")) and len(clean(v["D"])) != 12:
            warning("ISIN_LENGTH", "Episodes", row, "D", "ISIN should contain 12 characters; historical identity still needs source review")
    version_groups = defaultdict(list)
    version_keys = Counter((key(r["values"].get("B")), r["values"].get("C")) for r in versions.values())
    for ident, record in versions.items():
        v, row = record["values"], record["row"]
        ep = key(v.get("B"))
        if ep not in episodes:
            error("UNKNOWN_EPISODE", "Versions", row, "B", "Version must refer to one unique episode")
        if not whole(v.get("C")):
            error("VERSION_NUMBER", "Versions", row, "C", "Version number must be a positive integer")
        if version_keys[(ep, v.get("C"))] > 1:
            error("DUPLICATE_VERSION", "Versions", row, "C", "Episode and version-number pair must be unique")
        start, end = day(v.get("D")), day(v.get("E"))
        if not start or not end or start > end:
            warning("CONDUCT_INTERVAL", "Versions", row, "D", "A bounded conduct interval remains unresolved")
        version_groups[ep].append((ident, record))

    # Obligations are created before evidence is counted. Missing versions still
    # carry three placeholder obligations; multiple citations cannot inflate credit.
    expected = set()
    for mid in scoped:
        expected.update(("matter", mid, f) for f in ["legal_status", "order_date"])
    for eid in scoped_episodes:
        expected.update(("episode", eid, f) for f in EPISODE_FIELDS)
        for vid, _ in version_groups[eid] or [(f"missing:{eid}", None)]:
            expected.update(("version", vid, f) for f in VERSION_FIELDS)
    audited, completed = set(), set()
    disclosure_candidates = defaultdict(list)
    source_verified = lambda v: key(v.get("F")) in {"stated on sebi website", "other verified source"}

    for ident, record in indexes["Evidence"].items():
        v, row = record["values"], record["row"]
        field = clean(v.get("E"))
        mid, eid, vid, oid = (key(v.get(c)) for c in ["B", "C", "D", "G"])
        if field not in FIELDS:
            error("EVIDENCE_FIELD", "Evidence", row, "E", "Unsupported evidence field"); continue
        slot = ("version", vid, field) if field in VERSION_FIELDS else (("episode", eid, field) if field in EPISODE_FIELDS else ("matter", mid, field))
        links = mid in matters
        if eid:
            links = links and eid in episodes and key(episodes[eid]["values"].get("B")) == mid
        if field in VERSION_FIELDS or field in EPISODE_FIELDS:
            links = links and bool(eid)
        if field in VERSION_FIELDS:
            links = links and vid in versions and key(versions[vid]["values"].get("B")) == eid
        if not links:
            error("EVIDENCE_LINK", "Evidence", row, "B", "Matter, episode and version must belong together"); continue
        p1, p2 = key(v.get("K")), key(v.get("M"))
        d1, d2 = day(v.get("L")), day(v.get("N"))
        reviewed = bool(p1 and p2 and p1 != p2 and p1 in people and p2 in people and d1 and d2 and d2 >= d1
                        and key(people[p2]["values"].get("C")) == "yes")
        outcome = key(v.get("O"))
        if not reviewed:
            warning("EVIDENCE_UNAUDITED", "Evidence", row, "M", "Distinct registered independent human audit and ordered review dates are required")
        if outcome == "confirmed unresolved" and reviewed and clean(v.get("I")):
            if slot in expected:
                completed.add(slot)
            continue
        if oid not in valid_orders or key(orders.get(oid, {}).get("values", {}).get("B")) != mid:
            error("EVIDENCE_ORDER", "Evidence", row, "G", "Cited order must be valid and belong to this matter"); continue
        order = orders[oid]["values"]
        if not whole(v.get("H")) or v["H"] > order["H"]:
            error("EVIDENCE_PAGE", "Evidence", row, "H", "Citation page must be within the known order page count"); continue
        if not clean(v.get("I")) or not clean(v.get("J")):
            warning("EVIDENCE_LOCATOR", "Evidence", row, "I", "A source locator and confidence value are required"); continue
        wanted = None
        if field in VERSION_FIELDS:
            wanted = versions[vid]["values"].get(VERSION_FIELDS[field])
        elif field in EPISODE_FIELDS:
            wanted = episodes[eid]["values"].get(EPISODE_FIELDS[field])
        elif field == "legal_status":
            wanted = matters[mid]["values"].get("F")
        elif field == "order_date":
            wanted = order.get("D")
        matches = bool(day(wanted) and day(wanted) == day(v.get("F"))) if field in {"conduct_start", "conduct_end", "order_date"} else bool(clean(wanted) and key(wanted) == key(v.get("F")))
        if not matches:
            error("EVIDENCE_VALUE", "Evidence", row, "F", "Extracted value does not match the referenced registry field"); continue
        if reviewed and outcome in {"agree", "corrected"} and cutoff:
            if slot in expected:
                audited.add(slot); completed.add(slot)
            if eid and key(v.get("AB")) == "yes":
                disclosure_candidates[eid].append((day(order["E"]), source_verified(order)))

    legal_ok, legal_unverified = [], []
    legal_keys = Counter()
    for record in tables.get("LegalStatus", []):
        v, row = record["values"], record["row"]
        mid, eid, oid = (key(v.get(c)) for c in ["A", "F", "G"])
        public, event = day(v.get("C")), day(v.get("B"))
        scope = key(v.get("E"))
        if mid not in matters:
            error("LEGAL_MATTER", "LegalStatus", row, "A", "Legal event must belong to one unique matter"); continue
        if not clean(v.get("D")) or not public or not event or public < event:
            error("LEGAL_EVENT", "LegalStatus", row, "B", "Legal event needs status and ordered date-only event/public dates"); continue
        if scope not in {"whole matter", "specific episode"} or (scope == "specific episode" and (eid not in episodes or key(episodes[eid]["values"].get("B")) != mid)):
            error("LEGAL_SCOPE", "LegalStatus", row, "E", "Legal scope must identify the correct matter or episode"); continue
        if oid not in valid_orders or key(orders.get(oid, {}).get("values", {}).get("B")) != mid:
            error("LEGAL_SOURCE", "LegalStatus", row, "G", "Legal event needs a valid source order in the same matter"); continue
        if cutoff and public > cutoff:
            error("AFTER_CUTOFF", "LegalStatus", row, "C", "Legal event is public after this release's cutoff"); continue
        lk = (mid, scope, eid if scope == "specific episode" else "", public)
        legal_keys[lk] += 1
        if legal_keys[lk] > 1:
            error("DUPLICATE_LEGAL_EVENT", "LegalStatus", row, "C", "Duplicate matter/scope/public-date event key")
        order = orders[oid]["values"]
        if not source_verified(order):
            legal_unverified.append(record)
            warning("SOURCE_DATE_UNVERIFIED", "LegalStatus", row, "G", "Retained for review; excluded from strict snapshots and documented-event counts")
        elif public < day(order["E"]):
            error("PUBLIC_BEFORE_SOURCE", "LegalStatus", row, "C", "Event cannot be publicly known before its verified supporting source")
        else:
            legal_ok.append(record)

    delays, excluded_disclosure = [], 0
    for eid in scoped_episodes:
        candidates = disclosure_candidates[eid]
        first = min((d for d, _ in candidates), default=None)
        verified = first is not None and any(d == first and ok for d, ok in candidates)
        if not verified:
            excluded_disclosure += 1; continue
        first_versions = [r for _, r in version_groups[eid] if r["values"].get("C") == 1]
        if len(first_versions) == 1 and day(first_versions[0]["values"].get("E")):
            delays.append((first - day(first_versions[0]["values"]["E"])).days)
    if expected - audited:
        readiness.append(f"{len(expected - audited)} required evidence slots lack valid independent audit")
    if not scoped:
        readiness.append("No in-scope study matters entered; row 5 examples are excluded")
    manifest_ids = data.get("selected_matter_ids")
    if manifest_ids is None:
        readiness.append("A separately preserved selected-matter manifest is required before accepting a frozen cohort")
        if frozen:
            error("FROZEN_MANIFEST_REQUIRED", "SelectionLog", 4, "A", "Provide --selection-manifest for a frozen workbook")
    else:
        manifest_keys = [key(v) for v in manifest_ids]
        if any(not k for k in manifest_keys) or len(set(manifest_keys)) != len(manifest_keys):
            error("MANIFEST_IDS", "SelectionLog", 4, "A", "Manifest IDs must be nonblank and unique")
        for ident in sorted(set(manifest_keys) - set(matters)):
            error("SAMPLED_MATTER_MISSING", "Matters", 4, "A", f"Frozen sample matter {ident} is absent; deleting a row cannot shrink the cohort")
        for ident in sorted(set(scoped) - set(manifest_keys)):
            error("UNSAMPLED_MATTER", "Matters", scoped[ident]["row"], "A", "In-scope matter is absent from the supplied sample manifest")
    snapshot = data.get("snapshot_date")
    if snapshot not in (None, ""):
        sd = day(snapshot)
        if sd is None:
            error("SNAPSHOT_DATE", "Snapshot", 3, "B", "Pilot snapshots require a date-only trading-session date")
        elif data.get("session_dates") is None:
            error("SESSION_CALENDAR_REQUIRED", "Snapshot", 3, "B", "Supply a verified session-date CSV to check this snapshot date")
        elif sd not in data["session_dates"]:
            error("NON_SESSION_SNAPSHOT", "Snapshot", 3, "B", "Snapshot date is absent from the supplied trading-session calendar")
    if key(data.get("gate_inputs", {}).get("leak_test")) == "failing":
        error("LEAK_TEST_FAILED", "Gates", 29, "C", "A recorded leakage failure requires correction before model results can be accepted")
    readiness.append("Source passages, reviewer identity, legal interpretation and actual market coverage require human verification")
    readiness.append("Model evaluation and research PASS/CONDITIONAL/FAIL are not computed by this preparation checker")
    diagnostics.sort(key=lambda d: (d["sheet"], d["cell"], d["code"]))
    metrics = {"matters": len(scoped), "episodes": len(scoped_episodes), "registered_people": len(people),
               "required_slots": len(expected), "valid_audited_slots": len(audited), "review_completed_slots": len(completed),
               "missing_valid_audit_slots": len(expected - audited),
               "audit_share": len(audited) / len(expected) if expected else None,
               "review_completion_share": len(completed) / len(expected) if expected else None,
               "documented_legal_events": len(legal_ok), "unverified_legal_events": len(legal_unverified),
               "verified_delay_observations": len(delays), "disclosure_excluded_episodes": excluded_disclosure,
               "verified_delay_median_days": median(delays) if delays else None}
    return {"validation_only": True, "research_decision": "NOT_EVALUATED",
            "protocol_status": "FROZEN" if frozen else "DRAFT", "diagnostics": diagnostics,
            "metrics": metrics, "readiness": readiness,
            "validation_status": "INVALID" if any(d["severity"] == "error" for d in diagnostics) else "VALID",
            "counts_provisional": any(key(r["values"].get("J")) != "yes" for r in scoped.values()) or any(d["severity"] == "error" for d in diagnostics)}
