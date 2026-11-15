"""Bounded acquisition of official SEBI sources for provisional review.

Downloads and extraction are observations, never human review, legal findings,
publication-date verification or research-sample selection.
"""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from http.client import HTTPException
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pypdf import PdfReader, __version__ as pypdf_version

from . import __version__

HOSTS = {"www.sebi.gov.in", "sebi.gov.in"}
PAGE_LIMIT = 2_000_000
PDF_LIMIT = 20_000_000


def validate_source_url(url):
    if not isinstance(url, str) or any(ord(c) < 33 for c in url) or "\\" in url:
        raise ValueError("Source URL contains whitespace or control characters")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or parsed.hostname not in HOSTS or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443):
        raise ValueError("Sources must use HTTPS on an explicitly allowed SEBI hostname, without credentials or a nonstandard port")
    return urlunsplit(("https", parsed.hostname, parsed.path or "/", parsed.query, ""))


class SafeRedirect(HTTPRedirectHandler):
    max_redirections = 4
    max_repeats = 2

    def __init__(self):
        super().__init__()
        self.redirects = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = validate_source_url(urljoin(req.full_url, newurl))
        if len(self.redirects) >= self.max_redirections:
            raise ValueError("Source redirect limit reached")
        self.redirects.append({"from": req.full_url, "to": target, "status": code})
        return super().redirect_request(req, fp, code, msg, headers, target)

    def http_error_302(self, req, fp, code, msg, headers):
        # urllib's default redirect handler drains the entire response body.
        # This GET-only collector closes it unread, then follows a checked URL.
        try:
            location = headers.get("location") or headers.get("uri")
            if not location:
                raise ValueError("Redirect has no destination")
            redirected = self.redirect_request(req, fp, code, msg, headers, location)
            if redirected is None:
                raise ValueError("Redirect method is unsupported")
        finally:
            fp.close()
        return self.parent.open(redirected, timeout=req.timeout)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def fetch_document(url, max_bytes=PDF_LIMIT, opener=None):
    url = validate_source_url(url)
    redirects = SafeRedirect()
    opener = opener or build_opener(redirects)
    request = Request(url, headers={"User-Agent": f"Evidrava/{__version__} (bounded academic feasibility source collection)", "Accept-Encoding": "identity"})
    with opener.open(request, timeout=20) as response:
        final = validate_source_url(response.geturl())
        if response.status != 200:
            raise ValueError(f"Source returned HTTP {response.status}")
        length = response.headers.get("Content-Length")
        if length:
            try:
                if int(length) > max_bytes:
                    raise ValueError("Source exceeds download byte limit")
            except ValueError:
                raise ValueError("Source has an invalid or excessive Content-Length") from None
        chunks, size = [], 0
        while True:
            chunk = response.read(min(65536, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
            if size > max_bytes:
                raise ValueError("Source exceeds streamed download byte limit")
        data = b"".join(chunks)
        if length and len(data) != int(length):
            raise ValueError("Source body length differs from Content-Length; download is incomplete")
        return {"requested_url": url, "final_url": final, "status": response.status,
                "content_type": response.headers.get("Content-Type", ""), "data": data,
                "sha256": sha256(data).hexdigest(), "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "redirects": redirects.redirects, "request_count": 1 + len(redirects.redirects)}


class DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        field = {"a": "href", "iframe": "src", "embed": "src", "object": "data"}.get(tag)
        if field and attr.get(field):
            self.links.append((tag, attr[field]))


def discover_pdf_links(html, page_url):
    page_url = validate_source_url(page_url)
    parser = DocumentLinks()
    parser.feed(html)
    candidates = {}
    for tag, href in parser.links:
        resolved = urljoin(page_url, href)
        split = urlsplit(resolved)
        values = parse_qs(split.query).get("file", [])
        if values:
            viewer = validate_source_url(resolved)
            for value in values:
                candidate = urljoin(viewer, value)
                if urlsplit(candidate).path.lower().endswith(".pdf"):
                    candidate = validate_source_url(candidate)
                    candidates.setdefault(candidate, {"url": candidate, "via": viewer})
        elif split.path.lower().endswith(".pdf"):
            candidate = validate_source_url(resolved)
            candidates.setdefault(candidate, {"url": candidate, "via": f"{tag}: {href}"})
    return [candidates[url] for url in sorted(candidates)]


def extract_pdf(blob):
    """Count PDF pages and extract native text; do not OCR or interpret claims."""
    if not blob.startswith(b"%PDF-"):
        return {"status": "ERROR", "page_count": None, "pages": [], "error": "Response does not have a PDF signature"}
    try:
        reader = PdfReader(BytesIO(blob), strict=True)
        if reader.is_encrypted:
            return {"status": "ENCRYPTED", "page_count": None, "pages": []}
        if len(reader.pages) > 500:
            return {"status": "ERROR", "page_count": len(reader.pages), "pages": [], "error": "PDF exceeds the 500-page extraction limit"}
        pages, errors = [], []
        text_size = 0
        for number, page in enumerate(reader.pages, 1):
            try:
                content = page.get_contents()
                if content is not None and len(content.get_data()) > 5_000_000:
                    raise ValueError("Page content exceeds extraction limit")
                text = page.extract_text() or ""
                text_size += len(text)
                if text_size > 10_000_000:
                    raise ValueError("Extracted text exceeds pilot limit")
                pages.append({"page": number, "text": text})
            except Exception as exc:
                errors.append({"page": number, "error": str(exc)[:500]})
                pages.append({"page": number, "text": "", "extraction_error": str(exc)[:500]})
        status = "ERROR" if errors else ("OK" if any(p["text"].strip() for p in pages) else "NO_TEXT")
        return {"status": status, "page_count": len(reader.pages), "pages": pages, "page_errors": errors}
    except Exception as exc:
        return {"status": "ERROR", "page_count": None, "pages": [], "error": str(exc)[:500]}


def collect_sources(records, out, fetcher=fetch_document, extractor=extract_pdf, delay_seconds=1.0, reference_provenance=None):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Output exists; choose a new source-packet directory")
    ids = [r["screening_id"] for r in records]
    if not 1 <= len(records) <= 30 or len(set(ids)) != len(ids) or any(not re.fullmatch(r"RECON-(?:0[1-9]|[12][0-9]|30)", sid) for sid in ids):
        raise ValueError("Choose 1 to 30 distinct original RECON-01 through RECON-30 identifiers")
    for record in records:
        validate_source_url(record["url"])
    out.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f".{out.name}-incomplete-", dir=out.parent))
    manifest = {"kind": "source-acquisition", "version": __version__, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "reference_provenance": reference_provenance, "python_version": sys.version.split()[0], "pypdf_version": pypdf_version,
                "collector_source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
                "records": [], "human_screening_completed": False, "research_decision": "NOT_EVALUATED",
                "publication_dates_verified": False, "native_pdf_text_only": True,
                "limits": {"max_records": 30, "page_bytes": PAGE_LIMIT, "pdf_bytes": PDF_LIMIT,
                           "socket_timeout_seconds": 20, "max_redirects_per_fetch": 4, "max_retries": 0},
                "limitations": ["Automated retrieval and text extraction are not human screening or independent audit",
                                "Listing dates, retrieval timestamps and HTTP Last-Modified are not verified publication dates",
                                "Page numbers are PDF page positions; printed page labels may differ",
                                "Native text may omit tables, scans or layout; inspect the original PDF",
                                "This fixed reconnaissance batch is not the random research sample"]}
    total_bytes = total_requests = fetch_count = 0

    def fetch(url, limit):
        nonlocal fetch_count, total_bytes, total_requests
        if fetch_count:
            time.sleep(max(0, delay_seconds))
        fetch_count += 1
        capture = fetcher(url, max_bytes=limit)
        if len(capture["data"]) > limit:
            raise ValueError("Fetcher returned more bytes than permitted")
        if sha256(capture["data"]).hexdigest() != capture["sha256"]:
            raise ValueError("Fetched bytes and fingerprint do not agree")
        validate_source_url(capture["final_url"])
        total_bytes += len(capture["data"])
        total_requests += capture.get("request_count", 1)
        return capture

    def save(capture, relative):
        path = scratch / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(capture["data"])
        return {**{k: v for k, v in capture.items() if k != "data"}, "path": relative, "bytes": len(capture["data"])}

    for original in records:
        sid = original["screening_id"]
        result = {"screening_id": sid, "title": original["title"], "listing_url": original["url"],
                  "listing_response_sha256": original["response_sha256"], "candidates": []}
        manifest["records"].append(result)
        try:
            direct = urlsplit(original["url"]).path.lower().endswith(".pdf")
            page = fetch(original["url"], PDF_LIMIT if direct else PAGE_LIMIT)
            if page["data"].startswith(b"%PDF-"):
                pdf = page
                result["candidates"] = [{"url": page["final_url"], "via": "direct PDF response"}]
            else:
                result["page_capture"] = save(page, f"records/{sid}/page.html")
                candidates = discover_pdf_links(page["data"].decode("utf-8", errors="replace"), page["final_url"])
                result["candidates"] = candidates
                if len(candidates) != 1:
                    result["status"] = "AMBIGUOUS" if candidates else ("PDF_INVALID" if direct else "NO_PDF")
                    continue
                pdf = fetch(candidates[0]["url"], PDF_LIMIT)
            if not pdf["data"].startswith(b"%PDF-"):
                result["rejected_capture"] = save(pdf, f"records/{sid}/rejected-response.bin")
                result["status"] = "PDF_INVALID"
                result["error"] = "Document response lacks a PDF signature; bytes retained without claiming a PDF"
                continue
            result["pdf_capture"] = save(pdf, f"records/{sid}/source.pdf")
            extraction = extractor(pdf["data"])
            result["extraction"] = {k: v for k, v in extraction.items() if k != "pages"}
            pages_path = f"records/{sid}/pages.json"
            (scratch / pages_path).write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (scratch / f"records/{sid}/text.txt").write_text("\n\n".join(f"=== PDF page {p['page']} ===\n{p['text']}" for p in extraction["pages"]), encoding="utf-8")
            result["extraction"]["path"] = pages_path
            result["status"] = "EXTRACTION_FAILED" if extraction["status"] == "ERROR" else "ACQUIRED"
        except (OSError, ValueError, KeyError, HTTPException) as exc:
            result["status"] = "FETCH_FAILED" if "pdf_capture" not in result else "EXTRACTION_FAILED"
            result["error"] = str(exc)[:1000]
    acquired = sum(r["status"] == "ACQUIRED" for r in manifest["records"])
    manifest.update({"status": "COMPLETE" if acquired == len(records) else ("PARTIAL" if acquired else "FAILED"),
                     "counts": {"requested": len(records), "acquired": acquired, "failed": len(records) - acquired},
                     "successful_response_bytes": total_bytes, "successful_response_requests_including_redirects": total_requests,
                     "fetch_attempts": fetch_count, "failed_request_counts_incomplete": acquired != len(records)})
    rows = "".join(f"<tr><td>{escape(r['screening_id'])}</td><td>{escape(r['title'])}</td><td>{escape(r['status'])}</td><td>" +
                   (f"<a href=\"{escape(r['pdf_capture']['path'])}\">Original PDF</a>" +
                    (f" · <a href=\"records/{escape(r['screening_id'])}/text.txt\">Page text</a> ({escape(r['extraction']['status'])})" if r.get("extraction", {}).get("path") else " · extraction failed")
                    if "pdf_capture" in r else escape(r.get("error", "Review discovered candidates in the manifest"))) + "</td></tr>" for r in manifest["records"])
    (scratch / "report.html").write_text(f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidrava source packets</title><style>body{{font:16px/1.6 system-ui;max-width:1100px;margin:3rem auto;padding:0 1rem;color:#173044}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.7rem;border-bottom:1px solid #ddd;text-align:left}}.status{{background:#e7f3f7;padding:1rem}}</style><h1>Evidrava source packets</h1><p class="status">{manifest['status']} · {acquired}/{len(records)} sources acquired. Human screening and independent audit remain pending.</p><p>Inspect the original PDF alongside machine-extracted text. Retrieval dates are not verified publication dates. No screening decision or human time was filled automatically.</p><table><tr><th>ID</th><th>Source</th><th>Acquisition</th><th>Review files</th></tr>{rows}</table><p>Page text is provisional. Scanned, encrypted or malformed documents require separate handling; consult <a href="manifest.json">the provenance manifest</a> for extraction status, source URLs and hashes.</p></html>""", encoding="utf-8")
    manifest["files"] = {p.relative_to(scratch).as_posix(): sha256(p.read_bytes()).hexdigest() for p in sorted(scratch.rglob("*")) if p.is_file()}
    (scratch / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if out.exists():
        raise ValueError("Output appeared concurrently; incomplete packet retained")
    os.rename(scratch, out)
    return manifest
