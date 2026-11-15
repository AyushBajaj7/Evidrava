"""Offline source-acquisition contracts; network requests are always mocked.

PDF_BYTES is an opaque transport fixture, not a valid authored PDF or evidence.
These tests do not execute the received workbook suite or contact SEBI.
"""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
from email.message import Message
from hashlib import sha256
from http.client import IncompleteRead
from io import StringIO
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError
from urllib.request import Request

from evidrava.sources import (
    SafeRedirect, collect_sources, discover_pdf_links, fetch_document,
    extract_pdf, validate_source_url,
)
from evidrava import __version__
from evidrava.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


PAGE_URL = "https://www.sebi.gov.in/enforcement/orders/nov-2026/fictional.html"
PDF_URL = "https://www.sebi.gov.in/sebi_data/attachdocs/nov-2026/fictional.pdf"
PDF_TWO = "https://www.sebi.gov.in/sebi_data/attachdocs/nov-2026/fictional-two.pdf"
PDF_BYTES = b"%PDF-1.4\n% opaque mocked transport payload\n%%EOF\n"


def record(number=1, url=PAGE_URL):
    return {
        "screening_id": f"RECON-{number:02}", "url": url,
        "title": f"Fictional acquisition fixture {number}",
        "listing_date_stratum": "2021-2025", "listing_date": "2025-01-02",
        "response_sha256": "a" * 64, "human_screening_decision": "",
        "human_reviewer_id": "", "screening_active_minutes": "",
    }


class Response:
    def __init__(self, data, url=PDF_URL, status=200, content_type="application/pdf", length=None):
        self.data, self.url, self.status = data, url, status
        self.position, self.read_sizes = 0, []
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if length is not None:
            self.headers["Content-Length"] = str(length)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def read(self, size=-1):
        self.read_sizes.append(size)
        end = len(self.data) if size is None or size < 0 else self.position + size
        result = self.data[self.position:end]
        self.position += len(result)
        return result


class Opener:
    def __init__(self, response):
        self.response, self.calls = response, []

    def open(self, request, timeout=20):
        self.calls.append((request.full_url, timeout))
        return self.response


class RedirectBody:
    """Redirect bodies must be closed, never drained by the fetch pipeline."""
    def __init__(self):
        self.closed = False
        self.read_calls = 0

    def close(self):
        self.closed = True

    def read(self, *_args):
        self.read_calls += 1
        raise AssertionError("Redirect response body must not be read")


class Fetcher:
    """Mapping values are (bytes, content_type) or an exception to raise."""
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def __call__(self, url, max_bytes=20_000_000):
        self.calls.append((url, max_bytes))
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        data, content_type = value
        return {
            "requested_url": url, "final_url": url, "status": 200,
            "content_type": content_type, "data": data,
            "sha256": sha256(data).hexdigest(),
            "retrieved_at_utc": "2026-11-13T12:00:00+00:00",
            "redirects": [], "request_count": 1,
        }


def extracted(_data):
    return {"status": "OK", "page_count": 1,
            "pages": [{"page": 1, "text": "Fictional extracted fixture text."}]}


class SourceURLTests(unittest.TestCase):
    def test_official_https_url_preserves_download_query(self):
        url = PDF_URL + "?download=1"
        self.assertEqual(validate_source_url(url), url)

    def test_unsafe_urls_rejected(self):
        unsafe = [
            "http://www.sebi.gov.in/a.pdf",
            "https://www.sebi.gov.in.evil.example/a.pdf",
            "https://notsebi.gov.in/a.pdf",
            "https://name:secret@www.sebi.gov.in/a.pdf",
            "https://www.sebi.gov.in:444/a.pdf",
            "https://127.0.0.1/a.pdf",
            "file:///tmp/a.pdf", "javascript:alert(1)", "/relative.pdf",
        ]
        for url in unsafe:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_source_url(url)

    def test_redirect_guard_rejects_forbidden_target_before_following(self):
        handler = SafeRedirect()
        for target in ["https://evil.example/a.pdf", "http://www.sebi.gov.in/a.pdf"]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                handler.redirect_request(Request(PAGE_URL), None, 302, "Found", {}, target)

    def test_redirect_guard_allows_official_https_target(self):
        redirected = SafeRedirect().redirect_request(Request(PAGE_URL), None, 302, "Found", {}, PDF_URL)
        self.assertEqual(redirected.full_url, PDF_URL)

    def test_redirect_limit_stops_before_fifth_follow(self):
        handler = SafeRedirect()
        request = Request(PAGE_URL)
        for i in range(4):
            request = handler.redirect_request(request, None, 302, "Found", {}, f"/redirect-{i}")
        self.assertEqual(len(handler.redirects), 4)
        with self.assertRaises(ValueError):
            handler.redirect_request(request, None, 302, "Found", {}, PDF_URL)
        self.assertEqual(len(handler.redirects), 4)

    def test_credentials_controls_and_backslashes_are_rejected(self):
        for url in [PDF_URL + "\n", PDF_URL + " a", "https://www.sebi.gov.in\\@evil.example/a.pdf",
                    "https://user@www.sebi.gov.in/a.pdf", "https://www.sebi.gov.in:invalid/a.pdf"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_source_url(url)

    def test_all_redirect_handlers_close_unread_before_following(self):
        for status in [301, 302, 303, 307, 308]:
            with self.subTest(status=status):
                handler = SafeRedirect()
                body = RedirectBody()
                request = Request(PAGE_URL)
                request.timeout = 20
                response = object()

                def open_after_close(redirected, timeout):
                    self.assertTrue(body.closed)
                    self.assertEqual(redirected.full_url, PDF_URL)
                    self.assertEqual(timeout, 20)
                    return response

                handler.parent = Mock()
                handler.parent.open.side_effect = open_after_close
                headers = Message()
                headers["Location"] = PDF_URL
                returned = getattr(handler, f"http_error_{status}")(request, body, status, "Found", headers)
                self.assertIs(returned, response)
                self.assertEqual(body.read_calls, 0)
                handler.parent.open.assert_called_once()
                self.assertEqual(handler.redirects, [{"from": PAGE_URL, "to": PDF_URL, "status": status}])

    def test_invalid_or_missing_redirect_location_closes_without_following(self):
        for location in [None, "https://evil.example/a.pdf", "http://www.sebi.gov.in/a.pdf"]:
            with self.subTest(location=location):
                handler = SafeRedirect()
                handler.parent = Mock()
                request = Request(PAGE_URL)
                request.timeout = 20
                body = RedirectBody()
                headers = Message()
                if location is not None:
                    headers["Location"] = location
                with self.assertRaises(ValueError):
                    handler.http_error_302(request, body, 302, "Found", headers)
                self.assertTrue(body.closed)
                self.assertEqual(body.read_calls, 0)
                handler.parent.open.assert_not_called()

    def test_redirect_http_handler_enforces_four_follow_limit(self):
        handler = SafeRedirect()
        handler.parent = Mock()
        handler.parent.open.side_effect = lambda request, timeout: request
        request = Request(PAGE_URL)
        bodies = []
        for i in range(4):
            request.timeout = 20
            body = RedirectBody()
            bodies.append(body)
            request = handler.http_error_302(request, body, 302, "Found", {"location": f"/redirect-{i}"})
        request.timeout = 20
        body = RedirectBody()
        bodies.append(body)
        with self.assertRaises(ValueError):
            handler.http_error_302(request, body, 302, "Found", {"location": PDF_URL})
        self.assertEqual(handler.parent.open.call_count, 4)
        self.assertEqual(len(handler.redirects), 4)
        self.assertTrue(all(body.closed and body.read_calls == 0 for body in bodies))


class DiscoveryTests(unittest.TestCase):
    def test_relative_and_absolute_links_deduplicate(self):
        html = f'<a href="/sebi_data/attachdocs/nov-2026/fictional.pdf">Download</a><iframe src="{PDF_URL}"></iframe>'
        found = discover_pdf_links(html, PAGE_URL)
        self.assertEqual([v["url"] for v in found], [PDF_URL])
        self.assertTrue(found[0]["via"])

    def test_embed_and_object_candidates(self):
        html = f'<embed src="{PDF_URL}"><object data="{PDF_TWO}"></object>'
        self.assertEqual({v["url"] for v in discover_pdf_links(html, PAGE_URL)}, {PDF_URL, PDF_TWO})

    def test_viewer_file_query_resolves_pdf(self):
        html = '<iframe src="/viewer.html?file=%2Fsebi_data%2Fattachdocs%2Fnov-2026%2Ffictional.pdf"></iframe>'
        self.assertEqual([v["url"] for v in discover_pdf_links(html, PAGE_URL)], [PDF_URL])

    def test_unsafe_pdf_candidate_is_not_silently_followed(self):
        with self.assertRaises(ValueError):
            discover_pdf_links('<a href="https://evil.example/file.pdf">Download</a>', PAGE_URL)

    def test_official_candidate_is_retained_and_unrelated_external_pdf_is_recorded(self):
        html = f'<a href="https://evil.example/appeal.pdf">Appeal</a><iframe src="{PDF_URL}"></iframe>'
        found, rejected = discover_pdf_links(html, PAGE_URL, include_rejections=True)
        self.assertEqual([candidate["url"] for candidate in found], [PDF_URL])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["url"], "https://evil.example/appeal.pdf")

    def test_script_text_and_ordinary_links_are_not_pdf_discovery(self):
        html = f'<script>var source = "{PDF_URL}";</script><a href="/home.html">Home</a>'
        self.assertEqual(discover_pdf_links(html, PAGE_URL), [])

    def test_viewer_cannot_hide_external_pdf(self):
        html = '<iframe src="/web/?file=https%3A%2F%2Fevil.example%2Forder.pdf"></iframe>'
        with self.assertRaises(ValueError):
            discover_pdf_links(html, PAGE_URL)


class FetchTests(unittest.TestCase):
    def test_exact_bytes_hash_and_transport_provenance(self):
        opener = Opener(Response(PDF_BYTES))
        result = fetch_document(PDF_URL, opener=opener)
        self.assertEqual(result["data"], PDF_BYTES)
        self.assertEqual(result["sha256"], sha256(PDF_BYTES).hexdigest())
        self.assertEqual((result["requested_url"], result["final_url"]), (PDF_URL, PDF_URL))
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["request_count"], 1)
        self.assertEqual(result["redirects"], [])
        self.assertTrue(result["retrieved_at_utc"])
        self.assertEqual(opener.calls, [(PDF_URL, 20)])

    def test_unsafe_url_rejected_before_open(self):
        opener = Opener(Response(PDF_BYTES))
        with self.assertRaises(ValueError):
            fetch_document("https://evil.example/a.pdf", opener=opener)
        self.assertEqual(opener.calls, [])

    def test_final_url_validated_even_with_injected_opener(self):
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, opener=Opener(Response(PDF_BYTES, url="https://evil.example/a.pdf")))

    def test_actual_stream_limit_without_content_length(self):
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, max_bytes=10, opener=Opener(Response(b"x" * 100)))

    def test_false_small_content_length_cannot_bypass_stream_limit(self):
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, max_bytes=10, opener=Opener(Response(b"x" * 100, length=1)))

    def test_large_declared_length_is_rejected(self):
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, max_bytes=10, opener=Opener(Response(b"short", length=100)))

    def test_http_failure_not_returned_as_success(self):
        with self.assertRaises((ValueError, OSError)):
            fetch_document(PDF_URL, opener=Opener(Response(b"not found", status=404)))

    def test_short_body_is_not_a_complete_download(self):
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, opener=Opener(Response(b"short", length=20)))

    def test_exact_stream_limit_is_accepted(self):
        result = fetch_document(PDF_URL, max_bytes=len(PDF_BYTES),
                                opener=Opener(Response(PDF_BYTES, length=len(PDF_BYTES))))
        self.assertEqual(result["data"], PDF_BYTES)

    def test_invalid_content_length_is_rejected_before_read(self):
        response = Response(PDF_BYTES, length="unknown")
        with self.assertRaises(ValueError):
            fetch_document(PDF_URL, opener=Opener(response))
        self.assertEqual(response.read_sizes, [])


class NativeExtractionTests(unittest.TestCase):
    def test_non_pdf_bytes_produce_explicit_error_without_pages(self):
        result = extract_pdf(b"<html>Access challenge</html>")
        self.assertEqual(result["status"], "ERROR")
        self.assertIsNone(result["page_count"])
        self.assertEqual(result["pages"], [])

    def test_malformed_pdf_is_not_reported_as_readable(self):
        result = extract_pdf(PDF_BYTES)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["pages"], [])
        self.assertTrue(result["error"])


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "new-run"

    def collect(self, records, fetcher, extractor=extracted):
        return collect_sources(records, self.out, fetcher=fetcher, extractor=extractor, delay_seconds=0)

    def assert_manifest_files(self, manifest):
        self.assertTrue(manifest["files"])
        for relative, digest in manifest["files"].items():
            path = self.out / relative
            self.assertTrue(path.resolve().is_relative_to(self.out.resolve()))
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), digest)

    def assert_report_links(self):
        html = (self.out / "report.html").read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', html):
            if not href.startswith(("https://", "http://", "#")):
                self.assertTrue((self.out / href).is_file(), f"Broken report link: {href}")

    def test_direct_pdf_preserves_bytes_and_does_not_create_human_claims(self):
        records = [record(url=PDF_URL)]
        before = deepcopy(records)
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        result = self.collect(records, fetcher)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["counts"], {"requested": 1, "acquired": 1, "failed": 0})
        self.assertEqual(result["records"][0]["status"], "ACQUIRED")
        self.assertFalse(result["human_screening_completed"])
        self.assertFalse(result["publication_dates_verified"])
        self.assertEqual(result["research_decision"], "NOT_EVALUATED")
        self.assertEqual(records, before)
        self.assertEqual((self.out / "records/RECON-01/source.pdf").read_bytes(), PDF_BYTES)
        self.assert_manifest_files(result)
        self.assert_report_links()

    def test_html_single_pdf_captures_page_and_pdf(self):
        html = f'<html><a href="{PDF_URL}">Order</a></html>'.encode()
        fetcher = Fetcher({PAGE_URL: (html, "text/html"), PDF_URL: (PDF_BYTES, "application/pdf")})
        result = self.collect([record()], fetcher)
        self.assertEqual(result["records"][0]["status"], "ACQUIRED")
        self.assertEqual([u for u, _ in fetcher.calls], [PAGE_URL, PDF_URL])
        self.assertEqual((self.out / "records/RECON-01/page.html").read_bytes(), html)
        self.assertEqual((self.out / "records/RECON-01/source.pdf").read_bytes(), PDF_BYTES)
        self.assertEqual(result["records"][0]["listing_response_sha256"], "a" * 64)
        self.assert_manifest_files(result)

    def test_ambiguous_page_does_not_arbitrarily_download_first_pdf(self):
        html = f'<a href="{PDF_URL}">One</a><a href="{PDF_TWO}">Two</a>'.encode()
        fetcher = Fetcher({PAGE_URL: (html, "text/html")})
        result = self.collect([record()], fetcher)
        item = result["records"][0]
        self.assertEqual(item["status"], "AMBIGUOUS")
        self.assertEqual(len(item["candidates"]), 2)
        self.assertEqual([u for u, _ in fetcher.calls], [PAGE_URL])
        self.assertFalse((self.out / "records/RECON-01/source.pdf").exists())
        self.assertEqual(result["counts"]["acquired"], 0)

    def test_no_pdf_is_explicit_and_not_success(self):
        fetcher = Fetcher({PAGE_URL: (b"<html>No document link</html>", "text/html")})
        result = self.collect([record()], fetcher)
        self.assertEqual(result["records"][0]["status"], "NO_PDF")
        self.assertEqual(result["status"], "FAILED")

    def test_html_disguised_as_pdf_is_invalid(self):
        fetcher = Fetcher({PDF_URL: (b"<html>Access challenge</html>", "application/pdf")})
        result = self.collect([record(url=PDF_URL)], fetcher)
        self.assertEqual(result["records"][0]["status"], "PDF_INVALID")
        self.assertEqual(result["counts"]["acquired"], 0)

    def test_partial_failure_preserves_successful_record(self):
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf"), PDF_TWO: URLError("mock timeout")})
        result = self.collect([record(1, PDF_URL), record(2, PDF_TWO)], fetcher)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["counts"], {"requested": 2, "acquired": 1, "failed": 1})
        self.assertEqual([r["status"] for r in result["records"]], ["ACQUIRED", "FETCH_FAILED"])
        self.assertEqual((self.out / "records/RECON-01/source.pdf").read_bytes(), PDF_BYTES)
        self.assertTrue(result["records"][1]["error"])
        self.assert_manifest_files(result)

    def test_incomplete_http_body_is_recorded_and_next_record_continues(self):
        fetcher = Fetcher({PDF_URL: IncompleteRead(b"partial", 100), PDF_TWO: (PDF_BYTES, "application/pdf")})
        result = self.collect([record(1, PDF_URL), record(2, PDF_TWO)], fetcher)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual([r["status"] for r in result["records"]], ["FETCH_FAILED", "ACQUIRED"])
        self.assertEqual(result["counts"], {"requested": 2, "acquired": 1, "failed": 1})
        self.assertIn("IncompleteRead", result["records"][0]["error"])
        self.assertEqual([url for url, _limit in fetcher.calls], [PDF_URL, PDF_TWO])
        self.assertFalse((self.out / "records/RECON-01/source.pdf").exists())
        self.assertEqual((self.out / "records/RECON-02/source.pdf").read_bytes(), PDF_BYTES)
        self.assert_manifest_files(result)

    def test_extraction_error_keeps_pdf_but_reports_failure(self):
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        failed = lambda _data: {"status": "ERROR", "page_count": None, "pages": []}
        result = self.collect([record(url=PDF_URL)], fetcher, failed)
        self.assertEqual(result["records"][0]["status"], "EXTRACTION_FAILED")
        self.assertEqual((self.out / "records/RECON-01/source.pdf").read_bytes(), PDF_BYTES)
        self.assertEqual(result["records"][0]["extraction"]["status"], "ERROR")

    def test_scanned_pdf_is_acquired_without_invented_text(self):
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        scanned = lambda _data: {"status": "NO_TEXT", "page_count": 1, "pages": [{"page": 1, "text": ""}]}
        result = self.collect([record(url=PDF_URL)], fetcher, scanned)
        self.assertEqual(result["records"][0]["status"], "ACQUIRED")
        self.assertEqual(result["records"][0]["extraction"]["status"], "NO_TEXT")
        self.assertFalse(result["human_screening_completed"])

    def test_encrypted_pdf_is_preserved_with_explicit_extraction_status(self):
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        encrypted = lambda _data: {"status": "ENCRYPTED", "page_count": None, "pages": []}
        result = self.collect([record(url=PDF_URL)], fetcher, encrypted)
        self.assertEqual(result["records"][0]["extraction"]["status"], "ENCRYPTED")
        self.assertIsNone(result["records"][0]["extraction"]["page_count"])
        self.assertEqual((self.out / "records/RECON-01/text.txt").read_text(encoding="utf-8"), "")
        self.assertFalse(result["human_screening_completed"])
        self.assert_report_links()

    def test_raised_extraction_error_keeps_pdf_without_broken_report_links(self):
        def failed(_data):
            raise ValueError("Synthetic parser failure")
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        result = self.collect([record(url=PDF_URL)], fetcher, failed)
        self.assertEqual(result["records"][0]["status"], "EXTRACTION_FAILED")
        self.assertEqual((self.out / "records/RECON-01/source.pdf").read_bytes(), PDF_BYTES)
        self.assert_report_links()

    def test_report_escapes_source_title(self):
        item = record(url=PDF_URL)
        item["title"] = '<script>alert("fixture")</script>'
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        self.collect([item], fetcher)
        html = (self.out / "report.html").read_text(encoding="utf-8")
        self.assertNotIn(item["title"], html)
        self.assertIn("&lt;script&gt;", html)

    def test_fetcher_hash_mismatch_is_not_persisted_as_source(self):
        def corrupted(url, max_bytes):
            capture = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})(url, max_bytes)
            capture["sha256"] = "0" * 64
            return capture
        result = self.collect([record(url=PDF_URL)], corrupted)
        self.assertEqual(result["records"][0]["status"], "FETCH_FAILED")
        self.assertFalse((self.out / "records/RECON-01/source.pdf").exists())
        self.assert_manifest_files(result)

    def test_non_pdf_response_to_discovered_candidate_is_retained_as_rejected(self):
        html = f'<a href="{PDF_URL}">Order</a>'.encode()
        rejected = b"<html>Not a PDF</html>"
        fetcher = Fetcher({PAGE_URL: (html, "text/html"), PDF_URL: (rejected, "application/pdf")})
        result = self.collect([record()], fetcher)
        self.assertEqual(result["records"][0]["status"], "PDF_INVALID")
        self.assertEqual((self.out / "records/RECON-01/rejected-response.bin").read_bytes(), rejected)
        self.assertFalse((self.out / "records/RECON-01/source.pdf").exists())
        self.assert_manifest_files(result)

    def test_empty_batch_is_rejected_before_fetch(self):
        fetcher = Fetcher({})
        with self.assertRaises(ValueError):
            self.collect([], fetcher)
        self.assertEqual(fetcher.calls, [])
        self.assertFalse(self.out.exists())

    def test_existing_output_is_not_overwritten(self):
        self.out.mkdir()
        sentinel = self.out / "keep.txt"
        sentinel.write_bytes(b"preserve me")
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        with self.assertRaises(ValueError):
            self.collect([record(url=PDF_URL)], fetcher)
        self.assertEqual(sentinel.read_bytes(), b"preserve me")
        self.assertEqual(fetcher.calls, [])
        self.assertEqual(list(self.out.iterdir()), [sentinel])

    def test_duplicate_ids_rejected_before_acquisition(self):
        fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
        with self.assertRaises(ValueError):
            self.collect([record(1, PDF_URL), record(1, PDF_URL)], fetcher)
        self.assertEqual(fetcher.calls, [])

    def test_unsafe_record_ids_cannot_become_output_paths(self):
        for bad in ["../outside", "RECON-00", "RECON-31", "RECON-01/../../outside"]:
            with self.subTest(identifier=bad):
                item = record(url=PDF_URL)
                item["screening_id"] = bad
                fetcher = Fetcher({PDF_URL: (PDF_BYTES, "application/pdf")})
                with self.assertRaises(ValueError):
                    self.collect([item], fetcher)
                self.assertEqual(fetcher.calls, [])


class SourceCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "new-run"

    def invoke(self, ids, reference=None):
        stdout, stderr = StringIO(), StringIO()
        args = ["collect-sources", "--ids", *ids, "--out", str(self.out)]
        if reference is not None:
            args += ["--reference", str(reference)]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_command_checks_real_reference_and_passes_only_explicit_records(self):
        result = {"status": "COMPLETE", "counts": {"requested": 2, "acquired": 2, "failed": 0}}
        with patch("evidrava.__main__.collect_sources", return_value=result) as collector:
            code, stdout, stderr = self.invoke(["RECON-03", "RECON-01"], ROOT / "pilot/screening/screening_30.csv")
        self.assertEqual(code, 0, stderr)
        records, out = collector.call_args.args
        self.assertEqual([r["screening_id"] for r in records], ["RECON-03", "RECON-01"])
        self.assertEqual(out, self.out)
        self.assertTrue(collector.call_args.kwargs["reference_provenance"])
        summary = json.loads(stdout)
        self.assertFalse(summary["human_screening_completed"])
        self.assertEqual(summary["research_decision"], "NOT_EVALUATED")

    def test_command_unknown_or_duplicate_ids_do_not_fetch(self):
        for identifiers in [["RECON-31"], ["RECON-01", "RECON-01"]]:
            with self.subTest(identifiers=identifiers):
                with patch("evidrava.__main__.load_reference", return_value=([record()], {"verified": True})), \
                     patch("evidrava.__main__.collect_sources") as collector:
                    code, stdout, stderr = self.invoke(identifiers)
                self.assertEqual(code, 4)
                collector.assert_not_called()
                self.assertIn("distinct identifiers", stderr)

    def test_command_reference_verification_failure_does_not_fetch(self):
        with patch("evidrava.__main__.load_reference", side_effect=ValueError("Reference fingerprint mismatch")), \
             patch("evidrava.__main__.collect_sources") as collector:
            code, stdout, stderr = self.invoke(["RECON-01"])
        self.assertEqual(code, 4)
        collector.assert_not_called()
        self.assertIn("fingerprint mismatch", stderr)

    def test_command_partial_and_failed_acquisition_have_nonzero_exit(self):
        for status in ["PARTIAL", "FAILED"]:
            with self.subTest(status=status):
                result = {"status": status, "counts": {"requested": 1, "acquired": 0, "failed": 1}}
                with patch("evidrava.__main__.load_reference", return_value=([record()], {"verified": True})), \
                     patch("evidrava.__main__.collect_sources", return_value=result):
                    code, stdout, stderr = self.invoke(["RECON-01"])
                self.assertEqual(code, 3, stderr)
                self.assertEqual(json.loads(stdout)["status"], status)

    def test_command_existing_output_stops_before_reference_and_network(self):
        self.out.mkdir()
        with patch("evidrava.__main__.load_reference") as reference, \
             patch("evidrava.__main__.collect_sources") as collector:
            code, stdout, stderr = self.invoke(["RECON-01"])
        self.assertEqual(code, 4)
        reference.assert_not_called()
        collector.assert_not_called()

    def test_old_and_new_module_commands_report_current_version(self):
        for module in ["evidrava", "sebi_benchmark"]:
            with self.subTest(module=module):
                run = subprocess.run([sys.executable, "-m", module, "--version"], cwd=ROOT,
                                     capture_output=True, text=True, timeout=20)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout.strip(), __version__)


if __name__ == "__main__":
    unittest.main()
