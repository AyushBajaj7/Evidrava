"""Offline, mechanically checked source notes; never human screening or audit."""
from datetime import date, datetime, timezone
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import quote

from . import __version__

JSON_LIMIT = 2_000_000
FILE_LIMIT = 32_000_000
NOTE_FIELDS = {"kind", "schema_version", "prepared_on", "prepared_by", "source_packet_manifest_sha256", "scope_basis", "records"}
RECORD_FIELDS = {"screening_id", "suggested_disposition", "rationale", "observations", "open_questions"}
OBSERVATION_FIELDS = {"summary", "page", "paragraph", "anchor"}
DISPOSITIONS = {"exclude_candidate", "uncertain", "include_candidate"}


def _hash(path):
    if path.stat().st_size > FILE_LIMIT:
        raise ValueError("Source packet file exceeds the bounded review limit")
    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            size += len(chunk)
            if size > FILE_LIMIT:
                raise ValueError("Source packet file exceeds the bounded review limit")
            digest.update(chunk)
    return digest.hexdigest()


def _json(path):
    if path.stat().st_size > JSON_LIMIT:
        raise ValueError("Review JSON exceeds the 2 MB limit")
    blob = path.read_bytes()
    if len(blob) > JSON_LIMIT:
        raise ValueError("Review JSON exceeds the 2 MB limit")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Nonfinite JSON value is unsupported: {value}")

    return json.loads(blob.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=invalid_constant), sha256(blob).hexdigest()


def _keys(value, allowed, label):
    if not isinstance(value, dict) or set(value) != allowed:
        raise ValueError(f"{label} requires exactly its declared fields; human review, audit and timing fields are not accepted")


def _text(value, label, limit=5000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be nonempty text within {limit} characters")
    return value


def _digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA-256 fingerprint")
    return value


def _source_path(packet, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Source path must be a relative POSIX path inside the packet")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or parts.as_posix() != relative:
        raise ValueError("Source path escapes or is not canonical within the packet")
    path = (packet / relative).resolve()
    if not path.is_relative_to(packet) or not path.is_file():
        raise ValueError("Source path escapes the packet or does not identify a file")
    return path


def _link(path, out):
    # Relative links keep source and brief together in a portable project ZIP.
    return quote(Path(os.path.relpath(path, out)).as_posix(), safe="/.-")


def _render(result):
    cards = []
    for record in result["records"]:
        observations = "".join(
            f"<li><p>{escape(item['summary'])}</p><p class=\"source\"><a href=\"{escape(item['citation_uri'])}\">PDF page {item['page']}</a> · {escape(item['paragraph'])}</p><blockquote>{escape(item['anchor'])}</blockquote></li>"
            for item in record["observations"])
        questions = "".join(f"<li>{escape(question)}</li>" for question in record["open_questions"])
        cards.append(f"<section><p class=\"eyebrow\">{escape(record['screening_id'])} · PENDING HUMAN REVIEW</p><h2>{escape(record['title'])}</h2><p><strong>Machine suggestion:</strong> {escape(record['suggested_disposition'])}</p><p>{escape(record['rationale'])}</p><h3>Source observations</h3><ol>{observations}</ol><h3>Open questions</h3><ul>{questions}</ul><p><a href=\"{escape(record['pdf_uri'])}\">Open original PDF</a></p></section>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidrava provisional screening brief</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;color:#173044;background:#f4f7f9;max-width:1050px;margin:2rem auto;padding:0 1rem}}h1,h2,h3{{line-height:1.25}}section{{padding:1.5rem;background:white;border:1px solid #d7e2e8;border-radius:8px;margin:1.5rem 0}}.banner{{padding:1.2rem;border-left:5px solid #b57212;background:#fff2d6}}.eyebrow,.source{{font-size:.9rem;color:#4b6271}}blockquote{{margin:.6rem 0;padding:.5rem 1rem;border-left:3px solid #b5cbd6;color:#384f60}}a{{color:#075e85}}li{{margin:.5rem 0}}code{{overflow-wrap:anywhere}}</style></head><body><main>
<h1>Evidrava provisional screening brief</h1><div class="banner"><strong>PROVISIONAL — human screening and independent audit pending</strong><br>Suggestions and source summaries are machine-assisted notes. No human decision, timing, reviewer signature or publication-date verification has been created.</div>
<p>{escape(result['scope_basis'])}</p><p>Prepared {escape(result['prepared_on'])} by {escape(result['prepared_by'])}. Mechanical citation checks passed: retained files match their hashes and each quoted anchor occurs on the referenced extracted page. These checks do not validate a summary's meaning or establish eligibility.</p>
{''.join(cards)}
<section><h2>Next human task</h2><p>Read the original PDF and decide whether each suggestion is supported. Record your own screening decision, reason, locator and actual activity times in the separate working CSV. Leave independent-audit fields unset until a distinct person performs that review. PDF positions may differ from printed page labels; native extraction may lose tables or layout.</p><p>The research decision remains NOT EVALUATED. This positional reconnaissance batch does not select the research sample.</p></section>
<p><a href="brief.json">Structured brief</a> · <a href="manifest.json">Output hashes</a> · <a href="{escape(result['source_packet_manifest_uri'])}">Source provenance</a></p>
</main></body></html>"""


def build_brief(packet, notes_path, out):
    """Check preserved citations and write a new provisional review directory."""
    packet, notes_path, out = Path(packet).resolve(), Path(notes_path).resolve(), Path(out).resolve()
    if out.exists():
        raise ValueError("Output exists; choose a new review-brief directory")
    if out.is_relative_to(packet):
        raise ValueError("Keep generated briefs outside the preserved source packet")
    try:
        os.path.relpath(packet, out)
    except ValueError:
        raise ValueError("Source packet and brief output must share a filesystem volume for portable links") from None
    source, manifest_digest = _json(packet / "manifest.json")
    notes, notes_digest = _json(notes_path)
    _keys(notes, NOTE_FIELDS, "Notes")
    if notes["kind"] != "provisional-screening-notes" or type(notes["schema_version"]) is not int or notes["schema_version"] != 1:
        raise ValueError("Notes require provisional-screening-notes schema version 1")
    prepared_on = _text(notes["prepared_on"], "Prepared date", 10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", prepared_on):
        raise ValueError("Prepared date must be an ISO date")
    date.fromisoformat(prepared_on)
    _text(notes["prepared_by"], "Prepared by", 150)
    if not notes["prepared_by"].startswith("AI-assisted"):
        raise ValueError("This brief requires explicit AI-assisted attribution")
    _text(notes["scope_basis"], "Scope basis")
    if _digest(notes["source_packet_manifest_sha256"], "Source manifest hash") != manifest_digest:
        raise ValueError("Source packet manifest changed or does not match these notes")
    if not isinstance(source, dict) or source.get("kind") != "source-acquisition":
        raise ValueError("Expected a source-acquisition packet")
    original_records = source.get("records")
    if not isinstance(original_records, list) or not 1 <= len(original_records) <= 30:
        raise ValueError("Source packet requires 1 to 30 records")
    files = source.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 150:
        raise ValueError("Source packet requires a bounded file manifest")
    paths = {}
    for relative, digest in files.items():
        path = _source_path(packet, relative)
        if path in paths.values():
            raise ValueError("Source manifest repeats a resolved file")
        if _hash(path) != _digest(digest, "File hash"):
            raise ValueError(f"Source packet file changed: {relative}")
        paths[relative] = path
    original = {}
    for record in original_records:
        if not isinstance(record, dict):
            raise ValueError("Source record must be an object")
        sid = record.get("screening_id")
        if not isinstance(sid, str) or not re.fullmatch(r"RECON-(?:0[1-9]|[12][0-9]|30)", sid) or sid in original:
            raise ValueError("Source packet IDs must be distinct original RECON identifiers")
        original[sid] = record
    if not isinstance(notes["records"], list) or len(notes["records"]) != len(original):
        raise ValueError("Notes must cover every source packet record exactly once")
    records, seen = [], set()
    for note in notes["records"]:
        _keys(note, RECORD_FIELDS, "Record note")
        sid = note["screening_id"]
        if not isinstance(sid, str) or sid not in original or sid in seen:
            raise ValueError("Notes contain an unknown or duplicate record ID")
        seen.add(sid)
        if not isinstance(note["suggested_disposition"], str) or note["suggested_disposition"] not in DISPOSITIONS:
            raise ValueError("Suggested disposition must be exclude_candidate, uncertain or include_candidate")
        _text(note["rationale"], "Rationale")
        if not isinstance(note["open_questions"], list) or not 1 <= len(note["open_questions"]) <= 20:
            raise ValueError("Keep 1 to 20 explicit open questions per record")
        for question in note["open_questions"]:
            _text(question, "Open question", 2000)
        if not isinstance(note["observations"], list) or not 1 <= len(note["observations"]) <= 20:
            raise ValueError("Keep 1 to 20 cited observations per record")
        record = original[sid]
        pdf = record.get("pdf_capture", {})
        extraction = record.get("extraction", {})
        if record.get("status") != "ACQUIRED" or not isinstance(pdf, dict) or not isinstance(extraction, dict) or extraction.get("status") != "OK":
            raise ValueError("Every brief record needs an acquired PDF and usable native text")
        pdf_path, pages_path = pdf.get("path"), extraction.get("path")
        if not isinstance(pdf_path, str) or not isinstance(pages_path, str) or pdf_path not in paths or pages_path not in paths:
            raise ValueError("Source PDF and page text must be listed in the packet manifest")
        if files[pdf_path] != _digest(pdf.get("sha256"), "Record PDF hash"):
            raise ValueError("Record PDF fingerprint differs from the packet manifest")
        pages_json, pages_digest = _json(paths[pages_path])
        if pages_digest != files[pages_path] or not isinstance(pages_json, dict):
            raise ValueError("Page text changed during review")
        page_count = pages_json.get("page_count")
        pages = pages_json.get("pages")
        if type(page_count) is not int or type(extraction.get("page_count")) is not int or not 1 <= page_count <= 500 or page_count != extraction["page_count"]:
            raise ValueError("Page count must be a known integer matching the source record")
        if pages_json.get("status") != "OK" or not isinstance(pages, list) or len(pages) != page_count:
            raise ValueError("Page text inventory is incomplete")
        for number, page in enumerate(pages, 1):
            if not isinstance(page, dict) or type(page.get("page")) is not int or page["page"] != number or not isinstance(page.get("text"), str):
                raise ValueError("Extracted pages must be unique contiguous PDF positions from 1")
        pdf_uri = _link(paths[pdf_path], out)
        observations = []
        for observation in note["observations"]:
            _keys(observation, OBSERVATION_FIELDS, "Observation")
            _text(observation["summary"], "Observation summary")
            _text(observation["paragraph"], "Paragraph locator", 300)
            anchor = _text(observation["anchor"], "Quote anchor", 1000)
            if not 3 <= len(anchor.split()) <= 35:
                raise ValueError("Quote anchors must contain 3 to 35 words")
            number = observation["page"]
            if type(number) is not int or not 1 <= number <= page_count:
                raise ValueError("Citation page must be a known PDF page position")
            if " ".join(anchor.split()) not in " ".join(pages[number - 1]["text"].split()):
                raise ValueError(f"Quote anchor not found on cited page: {sid}, page {number}")
            observations.append({**observation, "citation_uri": f"{pdf_uri}#page={number}"})
        records.append({**note, "title": _text(record.get("title"), "Source title", 2000),
                        "status": "PENDING_HUMAN_REVIEW", "source_pdf_sha256": files[pdf_path],
                        "source_pages_sha256": pages_digest, "pdf_uri": pdf_uri, "observations": observations})
    # A concurrent input edit must not make the generated provenance inaccurate.
    if _hash(packet / "manifest.json") != manifest_digest or _hash(notes_path) != notes_digest:
        raise ValueError("Review inputs changed during analysis")
    for relative, path in paths.items():
        if _hash(path) != files[relative]:
            raise ValueError(f"Source packet changed during analysis: {relative}")
    result = {"kind": "provisional-screening-brief", "version": __version__,
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "prepared_on": prepared_on,
              "prepared_by": notes["prepared_by"], "scope_basis": notes["scope_basis"],
              "status": "PROVISIONAL", "citation_checks": "PASSED", "human_screening_completed": False,
              "independent_audit_completed": False, "publication_dates_verified": False,
              "research_decision": "NOT_EVALUATED", "source_packet_manifest_sha256": manifest_digest,
              "source_packet_manifest_uri": _link(packet / "manifest.json", out),
              "notes_sha256": notes_digest, "notes_name": notes_path.name,
              "source_file_hashes": files, "verified_source_files": len(files),
              "code_sha256": {p.name: _hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
              "records": sorted(records, key=lambda record: record["screening_id"]),
              "limitations": ["Mechanical quote and hash checks do not verify summaries or legal meaning",
                              "Machine suggestions are not human screening decisions or independent audit",
                              "Order dates, listing dates and retrieval dates do not verify public availability",
                              "Quoted page positions may differ from printed page labels",
                              "No human activity time was measured or filled by this command"]}
    out.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f".{out.name}-incomplete-", dir=out.parent))
    (scratch / "brief.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (scratch / "report.html").write_text(_render(result), encoding="utf-8")
    manifest = {"kind": "provisional-screening-brief", "completed": True, "publication": "local_only",
                "files": {path.name: _hash(path) for path in sorted(scratch.iterdir())}}
    (scratch / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if out.exists():
        raise ValueError("Output appeared concurrently; incomplete review brief retained")
    os.rename(scratch, out)
    return result
