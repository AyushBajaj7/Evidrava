"""Capture at most twelve explicitly planned official predecessor sources.

No crawling, publication-date verification, human review or registry updates.
"""
import argparse
from datetime import datetime, timezone
from email.message import Message
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evidrava.sources import PAGE_LIMIT, PDF_LIMIT, extract_pdf, fetch_document, validate_source_url


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        elif not self.hidden and tag in {"br", "hr", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")
        elif not self.hidden and tag in {"td", "th"}:
            self.parts.append("\t")

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)

    def text(self):
        return "\n".join(line for raw in "".join(self.parts).splitlines() if (line := " ".join(raw.split()))) + "\n"


def decode_html(blob, content_type):
    message = Message(); message["Content-Type"] = content_type
    header = message.get_content_charset()
    meta = re.search(r'<meta\b[^>]*charset\s*=\s*[\"\']?\s*([a-zA-Z0-9._-]+)', blob[:8192].decode("latin-1"), re.I)
    candidates = [("utf-8-sig", "BOM")] if blob.startswith(b"\xef\xbb\xbf") else []
    candidates += [(header, "HTTP charset"), (meta.group(1) if meta else None, "HTML meta charset"),
                   ("utf-8", "UTF-8 fallback"), ("windows-1252", "legacy fallback"), ("latin-1", "lossless byte fallback")]
    failures = []
    for encoding, basis in candidates:
        if not encoding:
            continue
        try:
            return blob.decode(encoding), {"encoding": encoding, "basis": basis, "failed_attempts": failures}
        except (LookupError, UnicodeError):
            failures.append(encoding)
    raise ValueError("Could not decode HTML")


def render_report(result):
    captured = sum(row["status"].startswith("CAPTURED") for row in result["sources"])
    cards = "".join(f"<section><h2>{escape(r['source_id'])}: {escape(r['title'])}</h2><p>{escape(r['relation_note'])}</p><p>{escape(r['status'])} · <a href=\"{escape(r['url'], quote=True)}\">Official source</a>" + (f" · <a href=\"{escape(r['capture']['path'])}\">Original PDF</a>" if r.get("capture", {}).get("path", "").endswith(".pdf") else "") + (f" · <a href=\"{escape(r['text_path'])}\">Page-labelled text</a>" if "text_path" in r else f" · {escape(r.get('error', ''))}") + "</p></section>" for r in result["sources"])
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidrava predecessor sources</title><style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#173044}}section{{border-top:1px solid #ccc;padding:1rem 0}}</style><h1>Predecessor source capture</h1><p>{result["status"]}: {captured}/{len(result["sources"])} sources captured. Source relationships, publication dates and first disclosure remain unverified; human review is pending.</p>{cards}<p>PDF text is labelled by PDF page. HTML text is a navigation aid rather than a stable page locator. Raw source bytes are retained for provenance. <a href="manifest.json">Capture manifest and hashes</a></p></html>'


def write_packet_manifest(packet, result):
    (packet / "report.html").write_text(render_report(result), encoding="utf-8")
    result["files"] = {p.relative_to(packet).as_posix(): sha256(p.read_bytes()).hexdigest()
                       for p in sorted(packet.rglob("*")) if p.is_file() and p.name != "manifest.json"}
    (packet / "manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def refresh_report(packet):
    """Regenerate a safe derived index after checking all retained source files."""
    packet = Path(packet).resolve()
    manifest_path = packet / "manifest.json"
    if not packet.is_dir() or not manifest_path.is_file():
        raise ValueError("Refresh requires an existing predecessor packet with manifest.json")
    result = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict) or result.get("kind") != "predecessor-source-capture":
        raise ValueError("Refresh requires a predecessor-source-capture manifest")
    files = result.get("files")
    if not isinstance(files, dict) or "report.html" not in files:
        raise ValueError("Packet manifest has no complete derived-file inventory")
    for name, digest in files.items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Packet manifest has an invalid file fingerprint")
        path = (packet / name).resolve()
        if not path.is_relative_to(packet) or not path.is_file():
            raise ValueError("Packet source file is missing or escapes the packet")
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Packet source file differs from its manifest")
    write_packet_manifest(packet, result)
    return result


def capture(plan_path, out, fetcher=fetch_document):
    plan_path, out = Path(plan_path).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError("Output exists; choose a new directory")
    if plan_path.stat().st_size > PAGE_LIMIT:
        raise ValueError("Capture plan exceeds the 2 MB limit")
    blob = plan_path.read_bytes()
    plan = json.loads(blob.decode("utf-8-sig"))
    if not isinstance(plan, dict) or set(plan) != {"kind", "sources"} or plan["kind"] != "predecessor-capture-plan":
        raise ValueError("Expected a predecessor-capture-plan with kind and sources")
    sources = plan["sources"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 12:
        raise ValueError("Plan requires one to twelve explicit sources")
    ids, urls = set(), set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"source_id", "screening_ids", "url", "title", "relation_note"}:
            raise ValueError("Each source requires exactly the declared source fields")
        sid = source["source_id"]
        if not isinstance(sid, str) or not re.fullmatch(r"PRE-(?:0[1-9]|1[0-2])", sid) or sid in ids:
            raise ValueError("Source IDs must be distinct PRE-01 through PRE-12")
        ids.add(sid)
        url = validate_source_url(source["url"])
        if url in urls:
            raise ValueError("Source URLs must be distinct")
        urls.add(url)
        linked = source["screening_ids"]
        if not isinstance(linked, list) or not linked or any(not isinstance(i, str) or not re.fullmatch(r"RECON-(?:0[1-9]|[12][0-9]|30)", i) for i in linked) or len(set(linked)) != len(linked):
            raise ValueError("Screening IDs must be distinct original RECON identifiers")
        if any(not isinstance(source[k], str) or not source[k].strip() or len(source[k]) > 5000 for k in ["title", "relation_note"]):
            raise ValueError("Source title and relation note must be nonempty bounded text")
    out.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f".{out.name}-incomplete-", dir=out.parent))
    result = {"kind": "predecessor-source-capture", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "plan_sha256": sha256(blob).hexdigest(), "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
              "sources": [], "human_review_completed": False, "publication_dates_verified": False,
              "first_disclosure_verified": False, "research_decision": "NOT_EVALUATED",
              "limits": {"max_sources": 12, "max_html_bytes": PAGE_LIMIT, "max_pdf_bytes": PDF_LIMIT, "socket_timeout_seconds": 20,
                         "max_redirects": 4, "automatic_retries": 0, "seconds_between_fetches": 1},
              "limitations": ["Candidate relationships and dates need source review; acquisition is not independent audit",
                              "Native HTML text may include navigation or lose table layout; exact source bytes are retained",
                              "Retrieval time, displayed dates and document signature dates are separate observations"]}
    for index, source in enumerate(sources):
        if index:
            time.sleep(1)
        row = {**source, "status": "FAILED"}; result["sources"].append(row)
        folder = scratch / source["source_id"]; folder.mkdir()
        try:
            expects_pdf = Path(source["url"].split("?", 1)[0]).suffix.lower() == ".pdf"
            response = fetcher(source["url"], max_bytes=PDF_LIMIT if expects_pdf else PAGE_LIMIT)
            data = response["data"]
            if not isinstance(data, bytes):
                raise ValueError("Fetcher did not return source bytes")
            limit = PDF_LIMIT if expects_pdf or data.startswith(b"%PDF-") else PAGE_LIMIT
            if len(data) > limit or sha256(data).hexdigest() != response["sha256"] or response["status"] != 200:
                raise ValueError("Response bytes, fingerprint, status or size are invalid")
            validate_source_url(response["final_url"])
            row["capture"] = {k: v for k, v in response.items() if k != "data"}
            content_type = response["content_type"]
            if data.startswith(b"%PDF-"):
                raw_name = "source.pdf"
                (folder / raw_name).write_bytes(data)
                row["capture"].update(path=f"{source['source_id']}/{raw_name}", bytes=len(data))
                extraction = extract_pdf(data)
                (folder / "pages.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                (folder / "text.txt").write_text("\n\n".join(f"=== PDF page {p['page']} ===\n{p['text']}" for p in extraction["pages"]), encoding="utf-8")
                row["extraction"] = {key: value for key, value in extraction.items() if key != "pages"}
                row["pages_path"] = f"{source['source_id']}/pages.json"
                row["text_path"] = f"{source['source_id']}/text.txt"
                if extraction["status"] == "ERROR":
                    row["status"] = "CAPTURED_EXTRACTION_ERROR"
                    row["error"] = "Original PDF retained; native text extraction failed"
                else:
                    row["status"] = "CAPTURED"
            else:
                is_html = content_type.split(";", 1)[0].strip().lower() in {"text/html", "application/xhtml+xml"}
                raw_name = "source.html" if is_html else "response.bin"
                (folder / raw_name).write_bytes(data)
                row["capture"].update(path=f"{source['source_id']}/{raw_name}", bytes=len(data))
                if not is_html:
                    raise ValueError("Expected HTML or a PDF-signature response; response retained as bytes")
                html, decoding = decode_html(data, content_type)
                if not re.search(r"<(?:html|head|body|p|div|table|font|h[1-6])(?:\s|>)", html, re.I):
                    raise ValueError("HTML response has no recognized document markup")
                parser = PlainText(); parser.feed(html); parser.close(); plain = parser.text()
                if not plain.strip():
                    raise ValueError("HTML has no readable native text")
                (folder / "text.txt").write_text(plain, encoding="utf-8")
                row.update(status="CAPTURED", decoding=decoding, text_path=f"{source['source_id']}/text.txt")
        except (OSError, ValueError, KeyError, TypeError, HTTPException) as exc:
            row["error"] = str(exc)[:1000]
    captured = sum(row["status"].startswith("CAPTURED") for row in result["sources"])
    result.update(status="COMPLETE" if captured == len(sources) else ("PARTIAL" if captured else "FAILED"),
                  counts={"requested": len(sources), "captured": captured, "failed": len(sources) - captured})
    write_packet_manifest(scratch, result)
    if out.exists():
        raise ValueError("Output appeared concurrently; incomplete capture retained")
    os.rename(scratch, out)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--refresh-report", type=Path, help="Regenerate a safe report for an existing verified packet")
    args = parser.parse_args(argv)
    try:
        if args.refresh_report:
            if args.plan or args.out:
                raise ValueError("--refresh-report cannot be combined with --plan or --out")
            result = refresh_report(args.refresh_report)
            print(json.dumps({"output": str(args.refresh_report.resolve()), "status": result["status"], **result["counts"]}))
            return 0
        if args.plan is None or args.out is None:
            raise ValueError("--plan and --out are required unless --refresh-report is used")
        result = capture(args.plan, args.out)
        print(json.dumps({"output": str(args.out.resolve()), "status": result["status"], **result["counts"]}))
        return 0 if result["status"] == "COMPLETE" else 3
    except (OSError, ValueError, TypeError) as exc:
        print(f"Capture could not complete: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
