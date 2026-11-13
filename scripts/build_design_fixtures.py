"""Build fictional design examples, not research data or executed acceptance results."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures" / "design"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = (
        "FICTIONAL TEST SOURCE. No real security, proceeding or reviewer.\n"
        "Synthetic episode E1 alleges a price-volume pattern during the dates below.\n"
        "Alleged episode E1 conduct_start: 2020-01-06\nconduct_end: 2020-01-08\n"
        "alleged_scheme: Fictional scheme\ninstrument: Fictional instrument\n"
        "isin: SYNTHETIC-ISIN\nlegal_status: Fictional interim allegation\n"
        "order_date: 2020-01-10\n"
    ).encode("utf-8")
    (OUT / "fictional_source.txt").write_bytes(source)
    stamp = "2026-11-05T12:00:00+05:30"
    fields = [
        ("conduct_start", "label_version", "V1", "date", "2020-01-06"),
        ("conduct_end", "label_version", "V1", "date", "2020-01-08"),
        ("alleged_scheme", "label_version", "V1", "text", "Fictional scheme"),
        ("instrument", "episode", "E1", "text", "Fictional instrument"),
        ("isin", "episode", "E1", "text", "SYNTHETIC-ISIN"),
        ("legal_status", "matter", "M1", "text", "Fictional interim allegation"),
        ("order_date", "matter", "M1", "date", "2020-01-10"),
    ]
    claims, evidence, reviews = [], [], []
    for n, (field, subject, target, kind, data) in enumerate(fields, 1):
        value = {"kind": kind, "data": data}
        claims.append({"id": f"C{n}", "subject_type": subject, "subject_id": target,
                       "field": field, "value": value, "revision": 1, "supersedes_id": None,
                       "recorded_at": stamp, "change_kind": "initial", "change_note": "Synthetic initial value"})
        evidence.append({"id": f"EV{n}", "claim_id": f"C{n}", "source_id": "S1", "order_id": "O1",
                         "locator": {"kind": "fixture_line", "line": n + 2}, "extracted_value": value,
                         "recorded_at": stamp})
        reviews.append({"id": f"R{n}", "subject_type": "evidence", "subject_id": f"EV{n}",
                        "extractor_id": "H1", "auditor_id": "H2", "extracted_on": "2026-11-04",
                        "audited_on": "2026-11-05", "outcome": "agreed",
                        "value_digest": digest({"claim_id": f"C{n}", "value": value}),
                        "rule_id": None, "note": "Fictional identities; no real human audit asserted"})
    reviews += [dict(reviews[0], id="R_inventory", subject_type="inventory", subject_id="M1", value_digest=None,
                     note="Synthetic inventory complete"),
                dict(reviews[0], id="R_group", subject_type="group", subject_id="G1", value_digest=None,
                     note="Synthetic independent group assignment")]
    bundle = {
        "schema_version": "0.1", "dataset_kind": "synthetic", "release_id": "fixture_release_1", "authored_at": stamp,
        "selected_claim_ids": [x["id"] for x in claims],
        "reviewers": [{"id": x, "display_name": f"Fictional reviewer {x}", "kind": "human"} for x in ["H1", "H2"]],
        "matters": [{"id": "M1", "independence_group_id": "G1", "review_state": "audited", "inventory_state": "complete",
                     "legal_history_state": "unknown", "legal_checked_on": "2026-11-05"}],
        "episodes": [{"id": "E1", "matter_id": "M1", "first_disclosure_evidence_id": "EV1",
                      "observability": "indeterminate", "observability_recorded_at": stamp}],
        "label_versions": [{"id": "V1", "episode_id": "E1", "version_no": 1, "supersedes_id": None,
                            "change_kind": "initial", "recorded_at": stamp, "change_note": "Synthetic initial version"}],
        "claims": claims,
        "sources": [{"id": "S1", "kind": "fixture_text", "uri": "urn:sebi:fictional-source:1",
                     "local_path": "fictional_source.txt", "sha256": hashlib.sha256(source).hexdigest(), "page_count": None,
                     "publication": {"basis": "verified", "precision": "timestamp", "value": "2020-01-10T10:00:00+05:30",
                                     "basis_source_id": "S1"}, "retrieved_at": stamp}],
        "orders": [{"id": "O1", "matter_id": "M1", "source_id": "S1", "order_date": "2020-01-10"}],
        "evidence": evidence, "reviews": reviews, "legal_events": [], "selection_events": []
    }
    config = {
        "schema_version": "0.1", "run_id": "design_example", "mode": "synthetic", "purpose": "registry_validation",
        "assessment_at": stamp, "deadline_at": "2026-12-04T23:59:59+05:30", "collection_cutoff": {"precision": "date", "value": "2020-01-15"}, "timezone": "Asia/Kolkata",
        "fit_cutoff": "2020-01-13T09:15:00+05:30", "score_time": "2020-01-13T09:15:00+05:30",
        "protocol": {"id": "synthetic_protocol", "state": "DRAFT", "frozen_at": None, "sha256": None,
                     "slot_policy": "all_included_versions", "slot_rules": [{"field": f, "subject_type": s,
                      "critical": f in ("conduct_start", "conduct_end", "instrument", "isin")} for f,s,_,_,_ in fields],
                     "date_only_policy": "next_session", "pass_min_episodes": 20, "conditional_min_episodes": 10,
                     "min_independent_groups": 10, "min_verified_share": 0.95, "warmup_sessions": 60,
                     "primary_horizon_years": 3, "sensitivity_horizon_years": [2,4],
                     "legal_policy_id": None, "universe_policy_id": None},
        "cohort": {"sample_manifest_sha256": None, "frame_sha256": None, "target_matters": 1, "inventory_complete": True,
                   "members": [{"matter_id": "M1", "episode_ids": ["E1"], "label_version_ids": ["V1"],
                                "inventory_review_id": "R_inventory"}]},
        "calendar": [{"session": day, "opens_at": day + "T09:15:00+05:30", "closes_at": day + "T15:30:00+05:30"}
                     for day in ["2020-01-06","2020-01-07","2020-01-08","2020-01-09","2020-01-10","2020-01-13"]],
        "artifact_refs": {"market_coverage_report": None, "identity_report": None, "leakage_report": None, "baseline_report": None}
    }
    report = {
        "schema_version": "0.1", "run_id": "design_example", "mode": "synthetic", "stage": "registry_validation",
        "research_decision": "DRAFT", "delivery_status": "IN_PROGRESS",
        "counts": {k: None for k in ["selected_matters","strict_episodes","independent_groups","expected_slots","verified_slots","reviewed_slots"]},
        "shares": {"verified": None, "review_completion": None, "denominator_complete": False}, "diagnostics": [],
        "checks": {"schema":"PASSED","domain":"NOT_RUN","market":"NOT_RUN","leakage":"NOT_RUN","baselines":"NOT_RUN"},
        "manifest_path": "manifest.json", "limitations": ["Illustrative output shape only; application/domain checks have not run."]
    }
    write("registry.json", bundle); write("run.json", config); write("example_report.json", report)
    mutations = [
        ("missing_episode_id", "AC01", "registry", "remove", "/episodes/0/id", None, False, "MISSING_ID"),
        ("bad_timestamp", "AC17", "run", "replace", "/score_time", "2020-13-99", False, "INVALID_TIMESTAMP"),
        ("fractional_page_count", "AC05", "registry", "replace", "/sources/0/page_count", 2.5, False, "INVALID_PAGE_COUNT"),
        ("unknown_field", "AC01", "registry", "add", "/unexpected", 1, False, "UNKNOWN_FIELD"),
        ("missing_evidence", "AC07", "registry", "remove", "/evidence/0", None, True, "MISSING_EVIDENCE; expected slots stay 7"),
        ("same_reviewer", "AC10", "registry", "replace", "/reviews/0/auditor_id", "H1", True, "REVIEW_NOT_INDEPENDENT"),
        ("wrong_value", "AC11", "registry", "replace", "/evidence/0/extracted_value/data", "2020-01-07", True, "VALUE_MISMATCH"),
        ("wrong_matter", "AC03", "registry", "replace", "/orders/0/matter_id", "M999", True, "UNKNOWN_REFERENCE"),
        ("duplicate_episode", "AC02", "registry", "append_copy", "/episodes", "/episodes/0", True, "DUPLICATE_EPISODE_ID"),
        ("deleted_episode", "AC09", "registry", "remove", "/episodes/0", None, True, "COHORT_REFERENCE_MISSING; obligations retained"),
        ("fit_after_score", "AC27", "run", "replace", "/fit_cutoff", "2020-01-14T09:15:00+05:30", True, "FIT_AFTER_SCORE_TIME"),
        ("fake_source_in_research", "AC25", "registry", "replace", "/dataset_kind", "research", True, "SYNTHETIC_SOURCE_IN_RESEARCH; mode mismatch")
    ]
    write("mutation_cases.json", [{"id": i,"scenario": a,"target": t,"operation": o,"path": p,"value": v,
                                   "schema_should_accept": ok,"domain_expected_not_executed": outcome}
                                  for i,a,t,o,p,v,ok,outcome in mutations])
    print("Built 3 JSON examples, 12 mutation definitions and one fictional text source.")


if __name__ == "__main__":
    main()
