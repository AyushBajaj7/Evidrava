"""Unit tests for the market data schema and consistency checker."""
import csv
from datetime import date
from pathlib import Path
import tempfile
import unittest

from evidrava.market_data import MARKET_FIELDS, inspect_market_data


def sample_row(**overrides):
    base = {
        "date": "2020-01-01",
        "isin": "INE002A01018",
        "symbol": "RELIANCE",
        "open": "1500.00",
        "high": "1520.00",
        "low": "1490.00",
        "close": "1510.00",
        "volume": "100000",
    }
    base.update(overrides)
    return base


def write_csv(path, rows, fields=None):
    fields = fields or MARKET_FIELDS
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "market_data.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_series_passes_with_status_valid(self):
        rows = [
            sample_row(date="2020-01-01"),
            sample_row(date="2020-01-02", open="1510.00", high="1530.00", low="1505.00", close="1525.00"),
            sample_row(date="2020-01-03", open="1525.00", high="1540.00", low="1515.00", close="1520.00"),
        ]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "VALID")
        self.assertEqual(report["summary"]["error_count"], 0)
        self.assertEqual(report["summary"]["total_rows"], 3)
        self.assertEqual(report["unique_isins"], ["INE002A01018"])
        self.assertEqual(report["summary"]["date_range"]["start"], "2020-01-01")
        self.assertEqual(report["summary"]["date_range"]["end"], "2020-01-03")

    def test_low_exceeds_high_detected(self):
        rows = [sample_row(high="1400.00", low="1500.00", open="1450.00", close="1450.00")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("LOW_EXCEEDS_HIGH", codes)

    def test_open_or_close_out_of_bounds_detected(self):
        rows = [sample_row(high="1500.00", low="1400.00", open="1550.00", close="1450.00")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("OPEN_OUT_OF_BOUNDS", codes)

    def test_negative_or_zero_price_rejected(self):
        rows = [sample_row(close="0.00", low="0.00")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("NON_POSITIVE_PRICE", codes)

    def test_negative_volume_rejected(self):
        rows = [sample_row(volume="-500")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("NEGATIVE_VOLUME", codes)

    def test_invalid_isin_rejected(self):
        rows = [sample_row(isin="SHORT_ISIN")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("INVALID_ISIN", codes)

    def test_duplicate_isin_and_date_rejected(self):
        rows = [sample_row(date="2020-01-01"), sample_row(date="2020-01-01")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("DUPLICATE_RECORD", codes)

    def test_chronology_violation_rejected(self):
        rows = [sample_row(date="2020-01-05"), sample_row(date="2020-01-02")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("CHRONOLOGY_VIOLATION", codes)

    def test_calendar_session_filtering(self):
        sessions = {date(2020, 1, 1), date(2020, 1, 2)}
        rows = [sample_row(date="2020-01-01"), sample_row(date="2020-01-03")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path, session_dates=sessions)
        self.assertEqual(report["status"], "INVALID")
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("NON_SESSION_DATE", codes)

    def test_warm_up_warning_generated(self):
        rows = [sample_row(date="2020-01-01")]
        write_csv(self.path, rows)
        report = inspect_market_data(self.path, min_warm_up_bars=10)
        self.assertEqual(report["status"], "VALID")  # warning does not invalidate
        self.assertEqual(report["summary"]["warning_count"], 1)
        codes = [d["code"] for d in report["diagnostics"]]
        self.assertIn("INSUFFICIENT_WARM_UP", codes)

    def test_missing_header_columns_raise_value_error(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("date,isin\n2020-01-01,INE002A01018\n")
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            inspect_market_data(self.path)


class MarketDataIntegrationTests(unittest.TestCase):
    def test_cli_check_market_data_writes_report_and_manifest(self):
        import subprocess
        import sys
        import json
        from hashlib import sha256
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "prices.csv"
            rows = [
                sample_row(date="2020-01-01"),
                sample_row(date="2020-01-02", open="1510.00", high="1530.00", low="1505.00", close="1525.00"),
            ]
            write_csv(data_path, rows)
            target = Path(tmp) / "report"
            cmd = [sys.executable, "-m", "evidrava", "check-market-data", "--data", str(data_path), "--out", str(target)]
            res = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            report = json.loads((target / "market_data.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "VALID")
            self.assertEqual(report["summary"]["total_rows"], 2)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            for name, digest in manifest["files"].items():
                self.assertEqual(sha256((target / name).read_bytes()).hexdigest(), digest)
            # Refuses overwrite
            again = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            self.assertEqual(again.returncode, 4)


if __name__ == "__main__":
    unittest.main()
