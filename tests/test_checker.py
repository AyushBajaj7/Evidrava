"""Synthetic preparation checks. These do not execute workbook formulas."""
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import load_workbook

from evidrava.checks import inspect_registry
from evidrava.workbook import load_registry

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx"
D = date


def row(number=6, **values):
    return {"row": number, "values": values}


def sample():
    """Fictional one-matter cohort with seven independently reviewed slots."""
    data = {"rules": {"B5": None, "B7": D(2025, 12, 31), "B8": 40, "B9": 20, "B10": 10,
                      "B11": .95, "B12": 3, "B13": 2, "B14": 4, "B15": 10, "B16": 60,
                      "B17": 1, "B18": "All versions", "B19": "Yes"}, "snapshot_date": None,
            "gate_inputs": {"leak_test": "Not run", "baselines": "Not run"}, "tables": {}}
    t = data["tables"]
    t["People"] = [row(A="Extractor Example", B="Extractor", C="No"), row(7, A="Auditor Example", B="Auditor", C="Yes")]
    t["Matters"] = [row(A="M1", B="Fictional matter", E="Audited (2nd reviewer)", F="Final order", G=D(2025, 12, 31), H="G1", I="Yes", J="Yes")]
    t["Orders"] = [row(A="O1", B="M1", C="Final order", D=D(2024, 6, 13), E=D(2024, 6, 14), F="Stated on SEBI website", H=10)]
    t["Episodes"] = [row(A="E1", B="M1", C="Fictional security", D="INE000000001", I="Complete", J="Complete", L="Yes")]
    t["Versions"] = [row(A="V1", B="E1", C=1, D=D(2024, 1, 1), E=D(2024, 2, 1), F="Alleged scheme")]
    t["LegalStatus"] = [row(A="M1", B=D(2024, 6, 13), C=D(2024, 6, 14), D="Final order", E="Whole matter", G="O1")]
    t["SelectionLog"] = [row(A="S1", C="Fictional candidate", F="Included", H="M1")]
    fields = [("legal_status", "Final order", None, None), ("order_date", D(2024, 6, 13), None, None),
              ("instrument", "Fictional security", "E1", None), ("isin", "INE000000001", "E1", None),
              ("conduct_start", D(2024, 1, 1), "E1", "V1"), ("conduct_end", D(2024, 2, 1), "E1", "V1"),
              ("alleged_scheme", "Alleged scheme", "E1", "V1")]
    t["Evidence"] = [row(6+i, A=f"X{i}", B="M1", C=eid, D=vid, E=field, F=value, G="O1", H=2,
                         I="Fictional paragraph 4", J="High", K="Extractor Example", L=D(2025, 1, 1),
                         M="Auditor Example", N=D(2025, 1, 2), O="Agree", AB="Yes" if field == "conduct_start" else "No")
                     for i, (field, value, eid, vid) in enumerate(fields)]
    return data


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.data = sample()

    def values(self, sheet, index=0):
        return self.data["tables"][sheet][index]["values"]

    def check(self, code=None):
        result = inspect_registry(self.data)
        if code:
            self.assertIn(code, {d["code"] for d in result["diagnostics"]})
        return result

    def test_complete_inputs_are_not_research_pass(self):
        r = self.check()
        self.assertEqual(r["validation_status"], "VALID")
        self.assertEqual(r["research_decision"], "NOT_EVALUATED")
        self.assertEqual(r["protocol_status"], "DRAFT")
        self.assertEqual(r["metrics"]["required_slots"], 7)
        self.assertEqual(r["metrics"]["valid_audited_slots"], 7)
        self.assertEqual(r["metrics"]["verified_delay_median_days"], 134)

    def test_missing_evidence_remains_in_denominator(self):
        self.data["tables"]["Evidence"].pop()
        r = self.check()["metrics"]
        self.assertEqual((r["required_slots"], r["valid_audited_slots"]), (7, 6))

    def test_missing_version_carries_placeholder(self):
        self.data["tables"]["Versions"] = []
        self.assertEqual(self.check()["metrics"]["required_slots"], 7)

    def test_all_versions_count_even_without_evidence(self):
        self.data["tables"]["Versions"].append(row(7, A="V2", B="E1", C=2, D=D(2024, 1, 1), E=D(2024, 2, 1), F="Correction"))
        r = self.check()["metrics"]
        self.assertEqual((r["required_slots"], r["valid_audited_slots"]), (10, 7))

    def test_unknown_page_count_cannot_accept_page_99(self):
        self.values("Orders")["H"] = None
        self.values("Evidence")["H"] = 99
        self.assertEqual(self.check("ORDER_PAGE_COUNT")["metrics"]["valid_audited_slots"], 0)

    def test_page_outside_known_bounds(self):
        self.values("Evidence")["H"] = 99
        self.check("EVIDENCE_PAGE")

    def test_duplicate_episode_quarantined(self):
        self.data["tables"]["Episodes"].append(deepcopy(self.data["tables"]["Episodes"][0]))
        self.assertEqual(self.check("DUPLICATE_ID")["validation_status"], "INVALID")

    def test_same_reviewer_gains_no_audit_credit(self):
        for r in self.data["tables"]["Evidence"]:
            r["values"]["M"] = "Extractor Example"
        self.assertEqual(self.check("EVIDENCE_UNAUDITED")["metrics"]["valid_audited_slots"], 0)

    def test_unregistered_reviewer(self):
        self.values("Evidence")["M"] = "Unknown person"
        self.assertEqual(self.check("EVIDENCE_UNAUDITED")["metrics"]["valid_audited_slots"], 6)

    def test_independence_required(self):
        self.values("People", 1)["C"] = "No"
        self.assertEqual(self.check()["metrics"]["valid_audited_slots"], 0)

    def test_reviewer_absence_allows_preparation(self):
        self.data = {**sample(), "tables": {name: [] for name in sample()["tables"]}}
        r = self.check()
        self.assertEqual(r["validation_status"], "VALID")
        self.assertIsNone(r["metrics"]["audit_share"])
        self.assertTrue(any("not registered" in x for x in r["readiness"]))

    def test_wrong_order(self):
        self.values("Orders")["B"] = "M404"
        self.check("EVIDENCE_ORDER")

    def test_wrong_value(self):
        self.values("Evidence")["F"] = "Unrelated status"
        self.assertEqual(self.check("EVIDENCE_VALUE")["metrics"]["valid_audited_slots"], 6)

    def test_future_order_cannot_support_evidence(self):
        self.values("Orders")["E"] = D(2026, 1, 1)
        self.assertEqual(self.check("AFTER_CUTOFF")["metrics"]["valid_audited_slots"], 0)

    def test_assumed_source_is_nonblocking_but_not_documented(self):
        self.values("Orders")["F"] = "Same as order date (assumed)"
        r = self.check("SOURCE_DATE_UNVERIFIED")
        self.assertEqual(r["validation_status"], "VALID")
        self.assertEqual(r["metrics"]["documented_legal_events"], 0)
        self.assertEqual(r["metrics"]["unverified_legal_events"], 1)
        self.assertEqual(r["metrics"]["verified_delay_observations"], 0)
        self.assertEqual(r["metrics"]["disclosure_excluded_episodes"], 1)

    def test_legal_public_before_verified_source(self):
        self.values("LegalStatus")["C"] = D(2024, 6, 13)
        self.check("PUBLIC_BEFORE_SOURCE")

    def test_missing_legal_status(self):
        self.values("LegalStatus")["D"] = None
        self.check("LEGAL_EVENT")

    def test_identity_only_evidence_does_not_set_disclosure(self):
        for r in self.data["tables"]["Evidence"]:
            r["values"]["AB"] = "No"
        self.assertEqual(self.check()["metrics"]["disclosure_excluded_episodes"], 1)

    def test_duplicate_included_new_guard(self):
        self.data["tables"]["SelectionLog"].append(row(7, A="S2", F="Included", H="M1"))
        self.assertEqual(self.check("DUPLICATE_INCLUDED_MATTER")["metrics"]["matters"], 1)

    def test_missing_selection_record(self):
        self.data["tables"]["SelectionLog"] = []
        self.check("SELECTION_ENTRY_MISSING")

    def test_missing_selection_decision(self):
        self.values("SelectionLog")["F"] = None
        self.check("SELECTION_DECISION_MISSING")

    def test_unknown_selected_matter(self):
        self.values("SelectionLog")["H"] = "M404"
        self.check("SELECTION_UNKNOWN_MATTER")

    def test_documented_exclusion_exempt(self):
        self.values("Matters")["E"] = "Excluded after review"
        self.values("SelectionLog").update(F="Excluded", G="Outside declared scope", H=None)
        r = self.check()
        self.assertEqual(r["validation_status"], "VALID")
        self.assertEqual(r["metrics"]["required_slots"], 0)

    def test_whitespace_id_is_missing(self):
        self.values("Orders")["A"] = "   "
        self.check("ID_MISSING")

    def test_unresolved_completes_review_without_audit_credit(self):
        self.values("Evidence").update(O="Confirmed unresolved", G=None, H=None)
        m = self.check()["metrics"]
        self.assertEqual((m["required_slots"], m["review_completed_slots"], m["valid_audited_slots"]), (7, 7, 6))

    def test_unresolved_requires_locator(self):
        self.values("Evidence").update(O="Confirmed unresolved", I=None)
        self.assertEqual(self.check()["metrics"]["review_completed_slots"], 6)

    def test_bad_review_date(self):
        self.values("Evidence")["N"] = D(2024, 1, 1)
        self.check("EVIDENCE_UNAUDITED")

    def test_dateonly_scope_rejects_intraday_publication(self):
        self.values("Orders")["E"] = datetime(2024, 6, 14, 14, 30)
        self.check("PUBLIC_DATE_INVALID")

    def test_snapshot_needs_calendar(self):
        self.data["snapshot_date"] = D(2024, 6, 17)
        self.check("SESSION_CALENDAR_REQUIRED")

    def test_non_session_snapshot(self):
        self.data.update(snapshot_date=D(2024, 6, 15), session_dates={D(2024, 6, 14), D(2024, 6, 17)})
        self.check("NON_SESSION_SNAPSHOT")

    def test_session_snapshot_allowed(self):
        self.data.update(snapshot_date=D(2024, 6, 17), session_dates={D(2024, 6, 17)})
        self.assertEqual(self.check()["validation_status"], "VALID")

    def test_frozen_requires_manifest(self):
        self.data["rules"]["B5"] = D(2025, 1, 1)
        self.check("FROZEN_MANIFEST_REQUIRED")

    def test_manifest_detects_deleted_matter(self):
        self.data["selected_matter_ids"] = ["M1", "M2"]
        self.check("SAMPLED_MATTER_MISSING")

    def test_policy_changes_are_diagnosed(self):
        for setting, value, code in [("B18", "Latest version only", "AUDIT_SCOPE"), ("B19", "No", "AUDITOR_POLICY"), ("B17", 0, "AVAILABILITY_LAG")]:
            with self.subTest(setting=setting):
                data = sample(); data["rules"][setting] = value
                self.assertIn(code, {d["code"] for d in inspect_registry(data)["diagnostics"]})

    def test_failed_leak_check_invalidates_preparation(self):
        self.data["gate_inputs"]["leak_test"] = "Failing"
        self.check("LEAK_TEST_FAILED")

    def test_input_not_mutated(self):
        before = deepcopy(self.data)
        self.check()
        self.assertEqual(self.data, before)


class WorkbookIntegrationTests(unittest.TestCase):
    def altered_in_memory(self, sheet, coordinate, value):
        # Mutate only a parser object. No spreadsheet file is authored or saved.
        workbook = load_workbook(TEMPLATE, data_only=False)
        workbook[sheet][coordinate] = value
        with patch("evidrava.workbook.load_workbook", return_value=workbook):
            return load_registry(TEMPLATE)

    def test_formula_tampering_is_detected(self):
        d = self.altered_in_memory("Gates", "B4", "PASS")
        self.assertIn("FORMULA_CHANGED", {i["code"] for i in d["loader_diagnostics"]})

    def test_changed_example_row_is_not_silently_skipped(self):
        d = self.altered_in_memory("Matters", "A5", "REAL-MATTER-IN-WRONG-ROW")
        self.assertIn("EXAMPLE_ROW_CHANGED", {i["code"] for i in d["loader_diagnostics"]})

    def test_header_layout_change_rejected(self):
        d = self.altered_in_memory("Evidence", "AB4", "Different meaning")
        self.assertIn("HEADER_MISMATCH", {i["code"] for i in d["loader_diagnostics"]})

    def test_overflow_is_not_silently_ignored(self):
        d = self.altered_in_memory("Matters", "A700", "M-OUTSIDE-RANGE")
        self.assertIn("INPUT_OVERFLOW", {i["code"] for i in d["loader_diagnostics"]})

    def test_formulas_in_input_rejected(self):
        d = self.altered_in_memory("Matters", "B6", "=1+1")
        self.assertIn("FORMULA_IN_INPUT", {i["code"] for i in d["loader_diagnostics"]})

    def test_received_template_signature_and_empty_study_rows(self):
        before = sha256(TEMPLATE.read_bytes()).hexdigest()
        data = load_registry(TEMPLATE)
        self.assertEqual(data["loader_diagnostics"], [])
        self.assertTrue(all(not records for records in data["tables"].values()))
        self.assertEqual(inspect_registry(data)["protocol_status"], "DRAFT")
        self.assertEqual(sha256(TEMPLATE.read_bytes()).hexdigest(), before)

    def test_cli_writes_report_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report"
            cmd = [sys.executable, "-m", "evidrava", "check-workbook", "--workbook", str(TEMPLATE), "--out", str(output)]
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            data = json.loads((output / "validation.json").read_text())
            self.assertEqual(data["research_decision"], "NOT_EVALUATED")
            self.assertIn("NOT EVALUATED", (output / "report.html").read_text())
            manifest = json.loads((output / "manifest.json").read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(sha256((output / name).read_bytes()).hexdigest(), digest)
            again = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(again.returncode, 4)
            self.assertIn("Output exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
