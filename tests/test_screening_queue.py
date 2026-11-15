"""Integration coverage for the source-backed human screening queue."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote

from evidrava.screening_queue import DEFAULT_SOURCE_PACKETS, build_screening_queue


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "pilot/screening/screening_30.csv"
PACKETS = [ROOT / packet for packet in DEFAULT_SOURCE_PACKETS]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


class ScreeningQueueTests(unittest.TestCase):
    def setUp(self):
        # Keep report links and preserved packet paths on D: even if the Python
        # temporary directory defaults to C: on this Windows machine.
        runs_dir = ROOT / "runs"
        runs_dir.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=runs_dir)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_verified_queue_covers_all_prepared_records_without_writes(self):
        before = {path: digest(path) for packet in PACKETS for path in packet.rglob("*") if path.is_file()}
        result = build_screening_queue(REFERENCE, PACKETS, self.root / "queue")
        self.assertEqual(result["status"], "SOURCE_QUEUE_READY")
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")
        self.assertIs(result["human_screening_completed"], False)
        self.assertEqual(result["source_preparation"], {
            "expected_records": 30, "acquired_records": 30,
            "extraction_statuses": {"ENCRYPTED": 1, "OK": 29},
        })
        self.assertEqual(len(result["records"]), 30)
        encrypted = next(record for record in result["records"] if record["screening_id"] == "RECON-08")
        self.assertEqual(encrypted["extraction_status"], "ENCRYPTED")
        self.assertIn("legitimate manual route", encrypted["human_action_required"])
        self.assertTrue(all(not record.get("human_screening_decision") for record in result["records"]))
        self.assertEqual(before, {path: digest(path) for packet in PACKETS for path in packet.rglob("*") if path.is_file()})

    def test_missing_source_packet_coverage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "coverage must match"):
            build_screening_queue(REFERENCE, PACKETS[:1], self.root / "queue")

    def test_cli_writes_portable_navigation_output_and_refuses_overwrite(self):
        target = self.root / "queue"
        command = [sys.executable, "-m", "evidrava", "screening-queue", "--out", str(target)]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        summary = json.loads(run.stdout)
        self.assertEqual(summary["acquired_records"], 30)
        report = json.loads((target / "screening-queue.json").read_text(encoding="utf-8"))
        self.assertEqual(report["source_preparation"]["extraction_statuses"], {"ENCRYPTED": 1, "OK": 29})
        self.assertTrue((target / "screening-queue.csv").read_text(encoding="utf-8").startswith("screening_id,"))
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        for name, value in manifest["files"].items():
            self.assertEqual(digest(target / name), value)
        html = (target / "report.html").read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', html):
            if not href.startswith(("https://", "http://", "#")):
                self.assertTrue((target / unquote(href)).is_file(), href)
        before = {path.name: path.read_bytes() for path in target.iterdir()}
        again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(again.returncode, 4)
        self.assertEqual(before, {path.name: path.read_bytes() for path in target.iterdir()})


if __name__ == "__main__":
    unittest.main()
