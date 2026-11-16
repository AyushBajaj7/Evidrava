"""Candidate-frame and deterministic sample-draw tests."""
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evidrava.frame import ALGORITHM, FRAME_FIELDS, draw_sample, inspect_frame


ROOT = Path(__file__).resolve().parents[1]


def rows():
    return [
        {"matter_id": "M1", "related_matter_group": "G1", "eligibility_status": "eligible", "eligibility_reason": "Synthetic eligible row"},
        {"matter_id": "M2", "related_matter_group": "G1", "eligibility_status": "eligible", "eligibility_reason": "Synthetic eligible row"},
        {"matter_id": "M3", "related_matter_group": "G2", "eligibility_status": "eligible", "eligibility_reason": "Synthetic eligible row"},
        {"matter_id": "M4", "related_matter_group": "G3", "eligibility_status": "eligible", "eligibility_reason": "Synthetic eligible row"},
        {"matter_id": "M5", "related_matter_group": "G3", "eligibility_status": "eligible", "eligibility_reason": "Synthetic eligible row"},
        {"matter_id": "M6", "related_matter_group": "", "eligibility_status": "pending", "eligibility_reason": "Needs source review"},
        {"matter_id": "M7", "related_matter_group": "", "eligibility_status": "excluded", "eligibility_reason": "Synthetic documented exclusion"}
    ]


def write_frame(path, data=None):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FRAME_FIELDS)
        writer.writeheader()
        writer.writerows(data or rows())


def write_protocol(path, frame_path, target=4, state="FROZEN", seed=123):
    protocol = {
        "protocol_id": "pilot_protocol",
        "state": state,
        "frozen_at": "2026-11-15T10:00:00+05:30",
        "frame_sha256": sha256(Path(frame_path).read_bytes()).hexdigest(),
        "sampling": {"algorithm": ALGORITHM, "seed": seed, "target_matters": target, "replacement_policy": "none"}
    }
    Path(path).write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")


class FrameTests(unittest.TestCase):
    def test_pinned_synthetic_fixture_binds_its_exact_frame_bytes(self):
        report, selection_blob = draw_sample(ROOT / "fixtures/frame/candidate-frame-synthetic.csv",
                                             ROOT / "fixtures/frame/frozen-protocol-synthetic.json")
        self.assertEqual(report["status"], "DRAWN")
        self.assertEqual(report["summary"]["selected_matters"], 4)
        self.assertIn(b'"selected_matter_ids"', selection_blob)

    def test_valid_frame_is_ready_to_freeze_with_declared_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            write_frame(frame_path)
            report = inspect_frame(frame_path)
            self.assertEqual(report["status"], "READY_TO_FREEZE")
            self.assertEqual(report["summary"], {"candidate_matters": 7, "eligible_matters": 5, "excluded_matters": 1,
                                                  "pending_matters": 1, "eligible_related_matter_groups": 3})
            self.assertEqual(report["eligible_groups"], {"G1": ["M1", "M2"], "G2": ["M3"], "G3": ["M4", "M5"]})
            self.assertEqual(report["diagnostics"], [])

    def test_invalid_rows_do_not_silently_become_a_freezable_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            data = rows()
            data[1]["matter_id"] = "M1"
            data[2]["related_matter_group"] = ""
            data[3]["eligibility_status"] = "included"
            data[4]["eligibility_reason"] = ""
            write_frame(frame_path, data)
            report = inspect_frame(frame_path)
            self.assertEqual(report["status"], "INVALID")
            self.assertTrue({"DUPLICATE_MATTER_ID", "GROUP_MISSING", "ELIGIBILITY_STATUS_INVALID", "ELIGIBILITY_REASON_MISSING"}
                            .issubset({item["code"] for item in report["diagnostics"]}))

    def test_draw_is_deterministic_exact_and_does_not_split_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            protocol_path = Path(tmp) / "protocol.json"
            write_frame(frame_path)
            write_protocol(protocol_path, frame_path)
            first, first_blob = draw_sample(frame_path, protocol_path)
            second, second_blob = draw_sample(frame_path, protocol_path)
            self.assertEqual(first, second)
            self.assertEqual(first_blob, second_blob)
            self.assertEqual(first["status"], "DRAWN")
            self.assertEqual(first["summary"]["selected_matters"], 4)
            selected = set(first["selected_matter_ids"])
            groups = inspect_frame(frame_path)["eligible_groups"]
            for group_id, members in groups.items():
                self.assertFalse(set(members) & selected and not set(members).issubset(selected), group_id)

    def test_frozen_protocol_refuses_changed_frame_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            protocol_path = Path(tmp) / "protocol.json"
            write_frame(frame_path)
            write_protocol(protocol_path, frame_path)
            frame_path.write_bytes(frame_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "FROZEN_INPUT_CHANGED"):
                draw_sample(frame_path, protocol_path)

    def test_target_that_cannot_preserve_groups_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            protocol_path = Path(tmp) / "protocol.json"
            data = rows()[:5]
            data[2]["related_matter_group"] = "G2"
            data[3]["related_matter_group"] = "G2"
            data[4]["related_matter_group"] = "G2"
            write_frame(frame_path, data)
            write_protocol(protocol_path, frame_path, target=4)
            with self.assertRaisesRegex(ValueError, "TARGET_NOT_REACHABLE"):
                draw_sample(frame_path, protocol_path)


class FrameIntegrationTests(unittest.TestCase):
    def test_frame_check_writes_an_integrity_manifest_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            target = Path(tmp) / "frame-report"
            write_frame(frame_path)
            command = [sys.executable, "-m", "evidrava", "frame-check", "--frame", str(frame_path), "--out", str(target)]
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads((target / "frame.json").read_text())
            self.assertEqual(report["status"], "READY_TO_FREEZE")
            manifest = json.loads((target / "manifest.json").read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(sha256((target / name).read_bytes()).hexdigest(), digest)
            again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(again.returncode, 4)

    def test_draw_requires_frozen_protocol_and_writes_workbook_compatible_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            protocol_path = Path(tmp) / "protocol.json"
            draft_path = Path(tmp) / "draft.json"
            target = Path(tmp) / "draw"
            rejected = Path(tmp) / "rejected"
            write_frame(frame_path)
            write_protocol(protocol_path, frame_path)
            write_protocol(draft_path, frame_path, state="DRAFT")
            bad = subprocess.run([sys.executable, "-m", "evidrava", "draw-sample", "--frame", str(frame_path), "--protocol", str(draft_path), "--out", str(rejected)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 3)
            self.assertFalse(rejected.exists())
            good = subprocess.run([sys.executable, "-m", "evidrava", "draw-sample", "--frame", str(frame_path), "--protocol", str(protocol_path), "--out", str(target)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            selection = json.loads((target / "selection-manifest.json").read_text())
            self.assertEqual(len(selection["selected_matter_ids"]), 4)
            self.assertEqual(selection["research_decision"], "NOT_EVALUATED")
            self.assertEqual(selection["selection_algorithm"], ALGORITHM)
            self.assertIn("selected_matter_ids", selection)

    def test_simulate_seeds_function_and_cli(self):
        from evidrava.seed_simulation import simulate_seeds
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame.csv"
            target = Path(tmp) / "sim-report"
            write_frame(frame_path)
            res = simulate_seeds(frame_path, target_matters=4, seed_count=5)
            self.assertEqual(res["status"], "COMPLETED")
            self.assertEqual(res["summary"]["successful_runs"], 5)
            cmd = [sys.executable, "-m", "evidrava", "simulate-seeds", "--frame", str(frame_path), "--target", "4", "--seeds", "5", "--out", str(target)]
            good = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            sim_json = json.loads((target / "simulation.json").read_text(encoding="utf-8"))
            self.assertEqual(sim_json["status"], "COMPLETED")
            self.assertTrue((target / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
