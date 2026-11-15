"""Build a read-only, hash-checked queue for human screening.

The queue joins the fixed 30-record reconnaissance CSV to already-preserved
official source packets.  It deliberately contains no eligibility decision,
reviewer identity, timing, audit credit or publication-date conclusion.
"""
from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote

from . import __version__
from .screening import load_reference


ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECON_ID = re.compile(r"^RECON-(?:0[1-9]|[12][0-9]|30)$")
DEFAULT_SOURCE_PACKETS = (
    Path("pilot/sources/recon-first-three"),
    Path("pilot/sources/recon-remaining-2026-11-16"),
    Path("pilot/sources/recon-retry-2026-11-16"),
)
QUEUE_FIELDS = [
    "screening_id", "listing_date_stratum", "title", "official_listing_url",
    "source_packet", "source_pdf", "page_text", "page_inventory",
    "extraction_status", "human_action_required",
]


def _digest(path):
    value = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


def _json(path):
    """Read JSON while rejecting duplicate keys and nonfinite values."""
    try:
        blob = Path(path).read_bytes()
    except OSError as exc:
        raise ValueError(f"Could not read JSON input: {Path(path).name}") from exc
    if len(blob) > 2_000_000:
        raise ValueError("Queue metadata exceeds the 2 MB pilot limit")

    def no_duplicates(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Nonfinite JSON value is unsupported: {value}")

    try:
        return json.loads(blob.decode("utf-8-sig"), object_pairs_hook=no_duplicates,
                          parse_constant=invalid_constant), sha256(blob).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Queue metadata must be valid UTF-8 JSON: {Path(path).name}") from exc


def _source_path(packet, relative):
    """Resolve one manifest path only when it remains inside its packet."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Source manifest path must be a relative POSIX path inside its packet")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or ".." in parts.parts or parts.as_posix() != relative:
        raise ValueError("Source manifest path escapes or is not canonical within its packet")
    path = (packet / relative).resolve()
    if not path.is_relative_to(packet) or not path.is_file():
        raise ValueError("Source manifest path escapes its packet or does not identify a file")
    return path


def _link(path, output_directory):
    """Create a portable local link instead of storing a machine-specific path."""
    return quote(Path(os.path.relpath(path, output_directory)).as_posix(), safe="/.-")


def _packet_label(packet):
    try:
        return packet.relative_to(ROOT).as_posix()
    except ValueError:
        return packet.name


def _on_same_volume(packet, output_directory):
    try:
        os.path.relpath(packet, output_directory)
    except ValueError:
        raise ValueError("Source packets and queue output must share a filesystem volume for portable links") from None


def _verify_packet(packet_path, reference_provenance, output_directory):
    """Verify every recorded packet file and expose acquired records only."""
    packet = Path(packet_path).resolve()
    if not packet.is_dir():
        raise ValueError(f"Source packet directory does not exist: {packet_path}")
    if output_directory.is_relative_to(packet):
        raise ValueError("Keep generated queues outside preserved source packets")
    _on_same_volume(packet, output_directory)
    manifest_path = packet / "manifest.json"
    manifest, manifest_sha256 = _json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("kind") != "source-acquisition":
        raise ValueError("Expected a source-acquisition packet manifest")
    if manifest.get("reference_provenance") != reference_provenance:
        raise ValueError("Source packet does not match the preserved reconnaissance reference")
    files = manifest.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 200:
        raise ValueError("Source packet requires a bounded file manifest")
    paths = {}
    for relative, fingerprint in sorted(files.items()):
        path = _source_path(packet, relative)
        if path in paths.values():
            raise ValueError("Source packet manifest repeats a resolved file")
        if not isinstance(fingerprint, str) or not SHA256.fullmatch(fingerprint):
            raise ValueError("Source packet file fingerprint must be a lowercase SHA-256 value")
        if _digest(path) != fingerprint:
            raise ValueError(f"Source packet file changed: {relative}")
        paths[relative] = path
    raw_records = manifest.get("records")
    if not isinstance(raw_records, list) or not 1 <= len(raw_records) <= 30:
        raise ValueError("Source packet must contain 1 to 30 record descriptions")
    records, seen = [], set()
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise ValueError("Source packet record must be an object")
        screening_id = raw.get("screening_id")
        if not isinstance(screening_id, str) or not RECON_ID.fullmatch(screening_id) or screening_id in seen:
            raise ValueError("Source packet IDs must be distinct original RECON identifiers")
        seen.add(screening_id)
        if raw.get("status") != "ACQUIRED":
            continue
        pdf = raw.get("pdf_capture")
        extraction = raw.get("extraction")
        if not isinstance(pdf, dict) or not isinstance(extraction, dict):
            raise ValueError("An acquired source record requires PDF and extraction metadata")
        pdf_relative = pdf.get("path")
        pages_relative = extraction.get("path")
        if not isinstance(pdf_relative, str) or not isinstance(pages_relative, str):
            raise ValueError("An acquired source record requires linked PDF and page inventory paths")
        if pdf_relative not in paths or pages_relative not in paths:
            raise ValueError("An acquired source record references a file missing from its packet manifest")
        if pdf.get("sha256") != files[pdf_relative]:
            raise ValueError("An acquired source PDF fingerprint differs from its packet manifest")
        extraction_status = extraction.get("status")
        if not isinstance(extraction_status, str) or not extraction_status:
            raise ValueError("An acquired source record requires an extraction status")
        text_relative = f"records/{screening_id}/text.txt"
        if text_relative not in paths:
            raise ValueError("An acquired source record requires its extracted-text navigation file")
        page_capture = raw.get("page_capture")
        listing_page_relative = page_capture.get("path") if isinstance(page_capture, dict) else None
        if listing_page_relative is not None and listing_page_relative not in paths:
            raise ValueError("A captured listing page must be present in its packet manifest")
        rejected = raw.get("rejected_candidates", [])
        if not isinstance(rejected, list):
            raise ValueError("Rejected source candidates must be a list when present")
        records.append({
            "screening_id": screening_id,
            "packet": _packet_label(packet),
            "packet_manifest_sha256": manifest_sha256,
            "source_pdf_sha256": files[pdf_relative],
            "extraction_status": extraction_status,
            "rejected_candidate_count": len(rejected),
            "pdf_path": paths[pdf_relative],
            "pages_path": paths[pages_relative],
            "text_path": paths[text_relative],
            "listing_page_path": paths[listing_page_relative] if listing_page_relative else None,
        })
    return records, {
        "packet": _packet_label(packet),
        "manifest_sha256": manifest_sha256,
        "verified_files": len(paths),
        "acquired_records": len(records),
        "packet_status": manifest.get("status"),
    }


def build_screening_queue(reference_path, source_packets, output_directory):
    """Return a mechanically verified queue without authoring human evidence."""
    output_directory = Path(output_directory).resolve()
    reference, reference_provenance = load_reference(reference_path)
    packet_paths = [Path(value).resolve() for value in source_packets]
    if not packet_paths or len(set(packet_paths)) != len(packet_paths):
        raise ValueError("Provide one or more distinct source packet directories")
    acquired, packet_checks = {}, []
    for packet in packet_paths:
        packet_records, packet_check = _verify_packet(packet, reference_provenance, output_directory)
        packet_checks.append(packet_check)
        for record in packet_records:
            screening_id = record["screening_id"]
            if screening_id in acquired:
                raise ValueError(f"More than one acquired source packet record exists for {screening_id}")
            acquired[screening_id] = record
    expected = {record["screening_id"]: record for record in reference}
    unexpected = sorted(set(acquired) - set(expected))
    missing = sorted(set(expected) - set(acquired))
    if unexpected or missing:
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if unexpected:
            detail.append("unexpected " + ", ".join(unexpected))
        raise ValueError("Source packet coverage must match the fixed reconnaissance batch: " + "; ".join(detail))
    records = []
    for source in reference:
        screening_id = source["screening_id"]
        material = acquired[screening_id]
        status = material["extraction_status"]
        action = (
            "Native text is unavailable because this PDF is encrypted. Inspect the original through a legitimate manual route before making any decision."
            if status == "ENCRYPTED"
            else "Open the original PDF; use extracted text only to navigate, then make and record a human decision."
        )
        records.append({
            "screening_id": screening_id,
            "listing_date_stratum": source["listing_date_stratum"],
            "title": source["title"],
            "official_listing_url": source["url"],
            "source_packet": material["packet"],
            "source_packet_manifest_sha256": material["packet_manifest_sha256"],
            "source_pdf_sha256": material["source_pdf_sha256"],
            "extraction_status": status,
            "rejected_candidate_count": material["rejected_candidate_count"],
            "human_action_required": action,
            "links": {
                "source_pdf": _link(material["pdf_path"], output_directory),
                "page_text": _link(material["text_path"], output_directory),
                "page_inventory": _link(material["pages_path"], output_directory),
                "captured_listing_page": _link(material["listing_page_path"], output_directory) if material["listing_page_path"] else None,
            },
        })
    extraction_counts = Counter(record["extraction_status"] for record in records)
    return {
        "kind": "screening-review-queue",
        "version": __version__,
        "status": "SOURCE_QUEUE_READY",
        "research_decision": "NOT_EVALUATED",
        "human_screening_completed": False,
        "independent_audit_completed": False,
        "publication_dates_verified": False,
        "reference_provenance": reference_provenance,
        "source_packet_checks": packet_checks,
        "source_preparation": {
            "expected_records": len(reference),
            "acquired_records": len(records),
            "extraction_statuses": dict(sorted(extraction_counts.items())),
        },
        "records": records,
        "human_work_checklist": [
            "Open the original source PDF and use its extracted text only as navigation aid.",
            "Decide include, exclude or uncertain; state the actual reason and source locator.",
            "Assess cash-equity scope and record a related-matter group or uncertainty.",
            "Search for predecessors, record the status and preserve supporting evidence.",
            "Record actual screening, grouping, predecessor-search and access-wait minutes separately in the working CSV.",
        ],
        "limitations": [
            "This is a fixed positional workload batch, not the random research sample.",
            "Verified file hashes establish packet integrity, not eligibility, legal meaning or public availability.",
            "The queue does not author human decisions, reviewer identities, timing observations or audit credit.",
            "PDF page positions can differ from printed page labels; native text can omit tables or layout.",
            "RECON-08 has an encrypted source PDF and cannot receive a decision from its empty native text.",
        ],
    }


def render_queue_csv(result):
    """Create a non-editable navigation export; human entries belong in working CSV."""
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=QUEUE_FIELDS, lineterminator="\n")
    writer.writeheader()
    for record in result["records"]:
        writer.writerow({
            "screening_id": record["screening_id"],
            "listing_date_stratum": record["listing_date_stratum"],
            "title": record["title"],
            "official_listing_url": record["official_listing_url"],
            "source_packet": record["source_packet"],
            "source_pdf": record["links"]["source_pdf"],
            "page_text": record["links"]["page_text"],
            "page_inventory": record["links"]["page_inventory"],
            "extraction_status": record["extraction_status"],
            "human_action_required": record["human_action_required"],
        })
    return stream.getvalue()
