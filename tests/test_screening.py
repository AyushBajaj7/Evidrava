"""Observed-workload semantics and offline screening command integration."""
from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evidrava.screening import FIELDS, HUMAN_FIELDS, load_reference, read_csv, summarize_screening

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "pilot/screening/screening_30.csv"


def reference_rows():
    records = []
    for i, stratum in enumerate(["2011-2015", "2011-2015", "2016-2020"]):
        r = {f: "" for f in FIELDS}
        r.update(screening_id=f"R{i+1}", listing_date_stratum=stratum, title=f"Fictional source {i+1}",
                 url=f"https://www.sebi.gov.in/example-{i+1}", machine_title_triage="uncertain_requires_document_review")
        records.append(r)
    return records


def fill(r, decision="include", minutes=(3, 2, 1), wait="0"):
    r.update(human_reviewer_id="Researcher Example", human_screening_decision=decision,
             human_decision_reason="Synthetic reason", document_opened="yes", eligibility_source_locator="Page 2 paragraph 3",
             cash_equity_scope="yes", group_key_or_uncertain="G1", predecessor_search_status="complete",
             predecessor_evidence="Synthetic predecessor search trail", followup_needed="no",
             screening_active_minutes=str(minutes[0]), grouping_active_minutes=str(minutes[1]),
             predecessor_active_minutes=str(minutes[2]), access_wait_minutes=str(wait))
    return r


class ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.reference = reference_rows()
        self.rows = deepcopy(self.reference)

    def report(self, code=None, count=None):
        report = summarize_screening(self.rows, self.reference, count)
        if code:
            self.assertIn(code, {d["code"] for d in report["diagnostics"]})
        return report

    def test_blank_batch_has_pending_records_and_no_invented_times(self):
        r = self.report()
        self.assertEqual(r["status"], "IN_PROGRESS")
        self.assertEqual(r["summary"]["pending_records"], 3)
        self.assertEqual(r["summary"]["complete_timing_observations"], 0)
        self.assertIsNone(r["summary"]["logged_active_minutes"])
        self.assertIsNone(r["summary"]["complete_active_minutes"]["median"])

    def test_golden_partial_and_wait_arithmetic(self):
        fill(self.rows[0], minutes=(3, 2, 1), wait=4)
        fill(self.rows[1], minutes=(2, 2, 1), wait=10)
        self.rows[2]["screening_active_minutes"] = "1"
        s = self.report()["summary"]
        self.assertEqual(s["complete_timing_observations"], 2)
        self.assertEqual(s["logged_active_minutes"], 12)
        self.assertEqual(s["complete_active_minutes"], {"observations": 2, "sum": 11, "mean": 5.5, "median": 5.5, "min": 5, "max": 6})
        self.assertEqual(s["observed_minutes"]["access_wait_minutes"], {"observations": 2, "total": 14})

    def test_zero_is_observed_and_blank_is_missing(self):
        fill(self.rows[0], minutes=(0, 0, 0))
        fill(self.rows[1], minutes=(1, 1, 1))
        self.rows[1]["grouping_active_minutes"] = ""
        s = self.report()["summary"]
        self.assertEqual(s["completed_screening_attempts"], 2)
        self.assertEqual(s["complete_timing_observations"], 1)
        self.assertEqual(s["complete_active_minutes"]["median"], 0)

    def test_invalid_timings(self):
        for value in ["-1", "NaN", "inf", "-inf", "unknown", "1e999"]:
            with self.subTest(value=value):
                self.rows = deepcopy(self.reference)
                fill(self.rows[0])["screening_active_minutes"] = value
                self.assertEqual(self.report("TIME_INVALID")["summary"]["complete_timing_observations"], 0)

    def test_uncertain_attempt_complete_but_unresolved(self):
        fill(self.rows[0], decision="uncertain").update(document_opened="no", eligibility_source_locator="",
            cash_equity_scope="uncertain", group_key_or_uncertain="uncertain", predecessor_search_status="uncertain",
            predecessor_evidence="", followup_needed="yes")
        s = self.report()["summary"]
        self.assertEqual((s["completed_screening_attempts"], s["complete_timing_observations"], s["unresolved_records"]), (1, 1, 1))
        self.assertEqual(s["decisions"], {"include": 0, "exclude": 0, "uncertain": 1})

    def test_finite_individual_times_cannot_overflow_record_total(self):
        fill(self.rows[0], minutes=(1e308, 1e308, 1e308))
        with self.assertRaisesRegex(ValueError, "finite numeric range"):
            self.report()

    def test_finite_records_cannot_overflow_batch_total(self):
        for row in self.rows:
            fill(row, minutes=(1e308, 0, 0))
        with self.assertRaisesRegex(ValueError, "finite numeric range"):
            self.report()

    def test_workload_scenario_overflow_is_rejected(self):
        for row in self.rows:
            fill(row, minutes=(3, 2, 1))
        with self.assertRaisesRegex(ValueError, "finite numeric range"):
            self.report(count=10 ** 400)

    def test_uncertain_cannot_be_marked_no_followup(self):
        fill(self.rows[0], decision="uncertain")
        self.report("FOLLOWUP_CONFLICT")

    def test_unopened_document_cannot_support_inclusion(self):
        fill(self.rows[0])["document_opened"] = "no"
        self.report("UNSUPPORTED_DECISION")

    def test_inclusion_scope_conflict(self):
        fill(self.rows[0])["cash_equity_scope"] = "no"
        self.report("SCOPE_CONFLICT")

    def test_missing_reviewer_and_reason_leave_attempt_pending(self):
        fill(self.rows[0]).update(human_reviewer_id="", human_decision_reason="")
        r = self.report()
        self.assertEqual(r["status"], "IN_PROGRESS")
        self.assertEqual(r["summary"]["completed_screening_attempts"], 0)

    def test_missing_locator_leaves_disposition_pending(self):
        fill(self.rows[0])["eligibility_source_locator"] = ""
        self.assertEqual(self.report()["summary"]["completed_screening_attempts"], 0)

    def test_completed_predecessor_search_needs_evidence(self):
        fill(self.rows[0])["predecessor_evidence"] = ""
        self.assertEqual(self.report()["summary"]["completed_screening_attempts"], 0)

    def test_machine_triage_is_never_human_review(self):
        self.rows[0]["machine_title_triage"] = "provisional_exclude_nontrading"
        r = self.report("METADATA_CHANGED")
        self.assertEqual(r["summary"]["completed_screening_attempts"], 0)

    def test_missing_original_row_does_not_shrink_target(self):
        self.rows.pop()
        r = self.report("RECORD_MISSING")
        self.assertEqual(r["summary"]["expected_records"], 3)
        self.assertEqual(r["missing_records"], ["R3"])

    def test_duplicate_ids_do_not_inflate_time(self):
        fill(self.rows[0])
        self.rows.append(deepcopy(self.rows[0]))
        self.assertEqual(self.report("DUPLICATE_ID")["summary"]["complete_timing_observations"], 0)

    def test_unknown_id(self):
        self.rows[0]["screening_id"] = "R404"
        self.report("UNKNOWN_ID")

    def test_fixed_metadata_changes_fail(self):
        self.rows[0]["response_sha256"] = "different"
        self.report("METADATA_CHANGED")

    def test_row_reordering_allowed(self):
        self.rows.reverse()
        self.assertEqual(self.report()["diagnostics"], [])

    def test_invalid_decision(self):
        fill(self.rows[0], decision="approved")
        self.report("DECISION_INVALID")

    def test_partial_cohort_cannot_produce_workload_projection(self):
        fill(self.rows[0])
        r = self.report(count=100)
        self.assertIsNone(r["planning_scenario"]["illustrative_initial_screening_hours"])
        self.assertIn("withheld_reason", r["planning_scenario"])

    def test_full_timing_cohort_has_explicit_planning_assumptions(self):
        for r in self.rows:
            fill(r, minutes=(3, 2, 1))
        result = self.report(count=100)
        self.assertEqual(result["status"], "READY_FOR_SCOPE_REVIEW")
        self.assertEqual(result["planning_scenario"]["illustrative_initial_screening_hours"], 10)
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")
        self.assertTrue(any("not a population estimate" in x for x in result["planning_scenario"]["assumptions"]))

    def test_strata_reconcile_and_empty_stratum_has_null_statistics(self):
        fill(self.rows[0])
        r = self.report()
        self.assertEqual(sum(s["expected_records"] for s in r["strata"].values()), 3)
        self.assertEqual(sum(s["complete_timing_observations"] for s in r["strata"].values()), 1)
        self.assertIsNone(r["strata"]["2016-2020"]["complete_active_minutes"]["median"])

    def test_missing_wait_does_not_invalidate_active_time(self):
        fill(self.rows[0], wait="")
        s = self.report()["summary"]
        self.assertEqual(s["complete_timing_observations"], 1)
        self.assertEqual(s["observed_minutes"]["access_wait_minutes"]["observations"], 0)

    def test_deterministic_and_does_not_mutate_inputs(self):
        before = deepcopy(self.rows)
        self.assertEqual(self.report(), self.report())
        self.assertEqual(self.rows, before)


class ScreeningIntegrationTests(unittest.TestCase):
    def test_original_and_nine_raw_captures_verified_without_writes(self):
        files = list((ROOT / "pilot/screening").rglob("*"))
        before = {p: sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
        rows, evidence = load_reference(REFERENCE)
        self.assertEqual(len(rows), 30)
        self.assertEqual(evidence["verified_raw_captures"], 9)
        self.assertEqual(before, {p: sha256(p.read_bytes()).hexdigest() for p in before})

    def test_duplicate_headers_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            p.write_text(",".join(FIELDS[:-1] + [FIELDS[0]]) + "\n")
            with self.assertRaisesRegex(ValueError, "27 columns"):
                read_csv(p)

    def test_wrong_row_width_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            p.write_text(",".join(FIELDS) + "\nonly-one-field\n")
            with self.assertRaisesRegex(ValueError, "wrong number"):
                read_csv(p)

    def test_cli_initial_progress_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "report"
            cmd = [sys.executable, "-m", "evidrava", "screening-report", "--csv", str(REFERENCE), "--out", str(target)]
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            report = json.loads((target / "screening.json").read_text())
            self.assertEqual(report["summary"]["pending_records"], 30)
            self.assertIsNone(report["summary"]["complete_active_minutes"]["median"])
            self.assertIn("IN_PROGRESS", (target / "report.html").read_text())
            manifest = json.loads((target / "manifest.json").read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(sha256((target / name).read_bytes()).hexdigest(), digest)
            again = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(again.returncode, 4)

    def test_cli_changed_metadata_reports_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "working.csv"
            rows, _ = read_csv(REFERENCE)
            rows[0]["title"] = "Changed title"
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
            target = Path(tmp) / "report"
            run = subprocess.run([sys.executable, "-m", "evidrava", "screening-report", "--csv", str(source), "--out", str(target)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 3, run.stderr)
            report = json.loads((target / "screening.json").read_text())
            self.assertEqual(report["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
