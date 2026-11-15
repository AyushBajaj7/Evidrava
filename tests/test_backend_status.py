"""Private, aggregate-only dashboard status coverage."""
from pathlib import Path
from unittest.mock import patch
import unittest

from backend.app import screening_progress


class BackendStatusTests(unittest.TestCase):
    def test_current_working_csv_reports_aggregate_pending_progress(self):
        status = screening_progress()
        self.assertEqual(status, {
            "expected_records": 30,
            "completed_attempts": 0,
            "complete_timing_observations": 0,
            "unresolved_records": 0,
            "status": "IN_PROGRESS",
            "input_integrity": "VALID",
        })

    def test_unavailable_working_csv_does_not_expose_error_detail(self):
        status = screening_progress(Path("does-not-matter.csv"), Path("missing-working.csv"))
        self.assertEqual(status, {
            "expected_records": 30,
            "completed_attempts": 0,
            "complete_timing_observations": 0,
            "unresolved_records": 30,
            "status": "INPUT_UNAVAILABLE",
            "input_integrity": "UNAVAILABLE",
        })

    def test_aggregate_completed_status_is_forwarded_without_csv_content(self):
        result = {"status": "READY_FOR_SCOPE_REVIEW", "summary": {
            "expected_records": 30,
            "completed_screening_attempts": 30,
            "complete_timing_observations": 30,
            "unresolved_records": 4,
        }}
        with patch("backend.app.load_reference", return_value=([{"screening_id": "RECON-01"}], {})), \
             patch("backend.app.read_csv", return_value=([{"screening_id": "RECON-01"}], "abc")), \
             patch("backend.app.summarize_screening", return_value=result):
            status = screening_progress(Path("reference.csv"), Path("working.csv"))
        self.assertEqual(status, {
            "expected_records": 30,
            "completed_attempts": 30,
            "complete_timing_observations": 30,
            "unresolved_records": 4,
            "status": "READY_FOR_SCOPE_REVIEW",
            "input_integrity": "VALID",
        })


if __name__ == "__main__":
    unittest.main()
