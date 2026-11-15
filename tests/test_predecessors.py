"""Offline checks for bounded predecessor HTML and PDF source capture."""
from copy import deepcopy
from hashlib import sha256
from http.client import IncompleteRead
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter

from scripts.capture_predecessors import capture, decode_html, refresh_report


URL = "https://www.sebi.gov.in/sebi_data/docfiles/example.html"
HTML = b'<html><head><style>HIDDEN STYLE</style><script>HIDDEN SCRIPT</script></head><body><h1>Example &amp; source</h1><p>First paragraph.</p><noscript>HIDDEN FALLBACK</noscript><p>Second paragraph.</p></body></html>'


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan_path, self.out = self.root / "plan.json", self.root / "out"
        self.plan = {"kind": "predecessor-capture-plan", "sources": [{
            "source_id": "PRE-01", "screening_ids": ["RECON-02"], "url": URL,
            "title": "Synthetic predecessor", "relation_note": "Candidate relationship only."}]}
        self.calls = []

    def fetcher(self, url, max_bytes):
        self.calls.append((url, max_bytes))
        return {"requested_url": url, "final_url": url, "status": 200, "content_type": "text/html; charset=utf-8",
                "data": HTML, "sha256": sha256(HTML).hexdigest(), "retrieved_at_utc": "2026-11-15T00:00:00+00:00",
                "redirects": [], "request_count": 1}

    def run_capture(self, fetcher=None):
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        with patch("scripts.capture_predecessors.time.sleep"):
            return capture(self.plan_path, self.out, fetcher=fetcher or self.fetcher)

    def test_html_capture_hashes_text_and_review_limits(self):
        original = deepcopy(self.plan)
        result = self.run_capture()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["counts"], {"requested": 1, "captured": 1, "failed": 0})
        self.assertEqual((self.out / "PRE-01/source.html").read_bytes(), HTML)
        plain = (self.out / "PRE-01/text.txt").read_text(encoding="utf-8")
        self.assertEqual(plain, "Example & source\nFirst paragraph.\nSecond paragraph.\n")
        self.assertNotIn("HIDDEN", plain)
        for name, digest in result["files"].items():
            self.assertEqual(sha256((self.out / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(result["plan_sha256"], sha256(self.plan_path.read_bytes()).hexdigest())
        self.assertEqual(self.calls, [(URL, 2_000_000)])
        self.assertEqual(self.plan, original)
        for key in ["human_review_completed", "publication_dates_verified", "first_disclosure_verified"]:
            self.assertIs(result[key], False)
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")

    def test_existing_output_is_not_overwritten(self):
        self.run_capture()
        before = (self.out / "manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            self.run_capture()
        self.assertEqual((self.out / "manifest.json").read_bytes(), before)
        self.assertEqual(len(self.calls), 1)

    def test_unsafe_urls_rejected_before_network(self):
        for url in ["http://www.sebi.gov.in/x", "https://evil.example/x", "file:///C:/x", None]:
            with self.subTest(url=url):
                self.plan["sources"][0]["url"] = url
                with self.assertRaises(ValueError):
                    self.run_capture()
                self.assertFalse(self.out.exists())
        self.assertFalse(self.calls)

    def test_unsafe_ids_and_missing_source_fields_rejected(self):
        initial = deepcopy(self.plan)
        for value in ["../escape", "PRE-13", True, ""]:
            self.plan = deepcopy(initial)
            self.plan["sources"][0]["source_id"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_capture()
        self.plan = deepcopy(initial)
        del self.plan["sources"][0]["relation_note"]
        with self.assertRaises(ValueError):
            self.run_capture()
        self.assertFalse(self.calls)

    def test_extended_predecessor_identifier_range_is_accepted(self):
        self.plan["sources"][0]["source_id"] = "PRE-12"
        result = self.run_capture()
        self.assertEqual(result["status"], "COMPLETE")
        self.assertTrue((self.out / "PRE-12/source.html").exists())

    def test_duplicate_sources_and_bad_screening_ids_rejected(self):
        initial = deepcopy(self.plan)
        self.plan["sources"].append(deepcopy(self.plan["sources"][0]))
        with self.assertRaises(ValueError):
            self.run_capture()
        self.plan["sources"][1]["source_id"] = "PRE-02"
        with self.assertRaises(ValueError):
            self.run_capture()
        for value in [[], ["RECON-31"], ["RECON-02", "RECON-02"], [False]]:
            self.plan = deepcopy(initial)
            self.plan["sources"][0]["screening_ids"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.run_capture()
        self.assertFalse(self.calls)

    def test_partial_http_failure_keeps_later_success(self):
        second = {**self.plan["sources"][0], "source_id": "PRE-02", "url": URL + "?second=1"}
        self.plan["sources"].append(second)

        def fetch(url, max_bytes):
            if url == URL:
                raise IncompleteRead(b"partial", 10)
            return self.fetcher(url, max_bytes)

        result = self.run_capture(fetch)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual([r["status"] for r in result["sources"]], ["FAILED", "CAPTURED"])
        self.assertTrue((self.out / "PRE-02/text.txt").exists())

    def test_pdf_response_is_retained_and_extracted(self):
        stream = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(stream)
        payload = stream.getvalue()

        def fetch(url, max_bytes):
            result = self.fetcher(url, max_bytes)
            result.update(data=payload, sha256=sha256(payload).hexdigest(), content_type="application/pdf")
            return result
        result = self.run_capture(fetch)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["sources"][0]["status"], "CAPTURED")
        self.assertEqual((self.out / "PRE-01/source.pdf").read_bytes(), payload)
        pages = json.loads((self.out / "PRE-01/pages.json").read_text(encoding="utf-8"))
        self.assertEqual(pages["page_count"], 1)
        self.assertTrue((self.out / "PRE-01/text.txt").exists())

    def test_plain_text_claimed_as_html_is_not_accepted(self):
        def fetch(url, max_bytes):
            result = self.fetcher(url, max_bytes)
            blob = b"No actual HTML document"
            result.update(data=blob, sha256=sha256(blob).hexdigest())
            return result
        result = self.run_capture(fetch)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue((self.out / "PRE-01/source.html").exists())

    def test_wrong_hash_and_unsafe_final_url_fail(self):
        for field, value in [("sha256", "0" * 64), ("final_url", "https://evil.example/x")]:
            with self.subTest(field=field):
                self.out = self.root / field

                def fetch(url, max_bytes):
                    result = self.fetcher(url, max_bytes)
                    result[field] = value
                    return result

                self.assertEqual(self.run_capture(fetch)["status"], "FAILED")

    def test_encoding_header_meta_and_explicit_legacy_fallback(self):
        body = '<html><p>Director\u2019s notice</p></html>'.encode("windows-1252")
        decoded, info = decode_html(body, "text/html; charset=windows-1252")
        self.assertIn("Director’s", decoded)
        self.assertEqual(info["basis"], "HTTP charset")
        decoded, info = decode_html(b'<meta charset="windows-1252">' + body, "text/html")
        self.assertIn("Director’s", decoded)
        self.assertEqual(info["basis"], "HTML meta charset")
        decoded, info = decode_html(body, "text/html; charset=utf-8")
        self.assertIn("Director’s", decoded)
        self.assertEqual(info["basis"], "legacy fallback")
        self.assertIn("utf-8", info["failed_attempts"])

    def test_report_escapes_notes_and_never_links_active_local_html(self):
        self.plan["sources"][0]["title"] = '<script>alert("bad")</script>'
        self.plan["sources"][0]["relation_note"] = '<b>Untrusted & provisional</b>'
        self.run_capture()
        report = (self.out / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn('href="PRE-01/text.txt"', report)
        self.assertNotIn('href="PRE-01/source.html"', report)

    def test_refresh_report_replaces_unsafe_derived_index_without_changing_sources(self):
        self.run_capture()
        source_before = (self.out / "PRE-01/source.html").read_bytes()
        report_path = self.out / "report.html"
        unsafe_report = report_path.read_text(encoding="utf-8").replace(
            'href="PRE-01/text.txt"', 'href="PRE-01/source.html"')
        report_path.write_text(unsafe_report, encoding="utf-8")
        manifest_path = self.out / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["report.html"] = sha256(unsafe_report.encode("utf-8")).hexdigest()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        result = refresh_report(self.out)

        self.assertEqual((self.out / "PRE-01/source.html").read_bytes(), source_before)
        report = report_path.read_text(encoding="utf-8")
        self.assertIn('href="PRE-01/text.txt"', report)
        self.assertNotIn('href="PRE-01/source.html"', report)
        refreshed = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, digest in refreshed["files"].items():
            self.assertEqual(sha256((self.out / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(result["status"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()
