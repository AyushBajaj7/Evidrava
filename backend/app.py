"""A bounded local HTTP API for the Evidrava pilot console.

The service never receives filesystem paths from the browser and never writes
to the workbook, screening CSV, source packets or project run directories.
Frame and protocol text is handled only in an operating-system temporary
directory for the duration of one request.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import csv
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evidrava import __version__
from evidrava.checks import day, inspect_registry
from evidrava.frame import draw_sample, inspect_frame
from evidrava.screening import load_reference, read_csv, summarize_screening
from evidrava.workbook import load_registry


MAX_REQUEST_BYTES = 2_500_000
MAX_WORKBOOK_REQUEST_BYTES = 32_000_000
MAX_WORKBOOK_BYTES = 20_000_000
MAX_AUXILIARY_TEXT_BYTES = 2_000_000
JSON_TYPE = "application/json; charset=utf-8"


def require_loopback_host(host: str) -> str:
    """Keep the standalone service deliberately local-only."""
    if host != "127.0.0.1":
        raise ValueError("Evidrava local services may bind only to 127.0.0.1")
    return host


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def error_response(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}, "research_decision": "NOT_EVALUATED"}


def read_text(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def screening_progress(reference_path: Path | None = None, working_path: Path | None = None) -> dict[str, Any]:
    """Summarize human-entered screening progress without exposing any entries.

    The dashboard receives only aggregate counts and input state.  Decisions,
    names, notes, source locators and timings remain in the local CSV and
    report files; neither is returned through the browser API.
    """
    reference_path = reference_path or ROOT / "pilot/screening/screening_30.csv"
    if working_path is None:
        candidate = ROOT / "working/screening_30.csv"
        working_path = candidate if candidate.is_file() else reference_path
    try:
        reference, _ = load_reference(reference_path)
        rows, _ = read_csv(working_path)
        result = summarize_screening(rows, reference)
        summary = result["summary"]
        return {
            "expected_records": summary["expected_records"],
            "completed_attempts": summary["completed_screening_attempts"],
            "complete_timing_observations": summary["complete_timing_observations"],
            "unresolved_records": summary["unresolved_records"],
            "status": result["status"],
            "input_integrity": "INVALID" if result["status"] == "INVALID" else "VALID",
        }
    except (OSError, ValueError, KeyError, TypeError):
        # Do not leak user-entered content or filesystem error detail into the
        # browser.  The CLI report remains the route for diagnostics.
        return {
            "expected_records": 30,
            "completed_attempts": 0,
            "complete_timing_observations": 0,
            "unresolved_records": 30,
            "status": "INPUT_UNAVAILABLE",
            "input_integrity": "UNAVAILABLE",
        }


def project_status() -> dict[str, Any]:
    """Expose only safe, non-authoritative local project state."""
    record_path = ROOT / "pilot/development/evidrava-live-screening-status-increment-2026-11-16.json"
    source_record_path = ROOT / "pilot/development/evidrava-source-preparation-2026-11-16.json"
    queue_record_path = ROOT / "pilot/development/evidrava-screening-queue-v0.7.1-2026-11-16/screening-queue.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        research = record.get("research_status", {})
        last_verified_increment = (
            record.get("software_version", "unknown")
            if record.get("status") == "COMPLETE"
            else "not-yet-verified"
        )
    except (OSError, json.JSONDecodeError):
        research = {}
        last_verified_increment = "unknown"
    try:
        source_record = json.loads(source_record_path.read_text(encoding="utf-8"))
        source_inventory = source_record.get("resolved_inventory", {})
        source_boundary = source_record.get("research_boundary", {})
    except (OSError, json.JSONDecodeError):
        source_record = {}
        source_inventory = {}
        source_boundary = {}
    try:
        queue_record = json.loads(queue_record_path.read_text(encoding="utf-8"))
        queue_inventory = queue_record.get("source_preparation", {})
    except (OSError, json.JSONDecodeError):
        queue_record = {}
        queue_inventory = {}
    return {
        "service": "evidrava-backend",
        "status": "ok",
        "software_version": __version__,
        "last_verified_increment": last_verified_increment,
        "research_status": {
            "protocol": "DRAFT",
            "reviewer_confirmed": bool(research.get("reviewer_confirmed", False)),
            "real_candidate_frame_created": bool(research.get("real_candidate_frame_created", False)),
            "real_protocol_frozen": bool(research.get("real_protocol_frozen", False)),
            "real_sample_drawn": bool(research.get("real_sample_drawn", False)),
            "research_decision": "NOT_EVALUATED"
        },
        "screening": screening_progress(),
        "source_preparation": {
            "status": source_record.get("status", "NOT_RECORDED"),
            "records_acquired": source_inventory.get("acquired_records", 0),
            "expected_records": source_inventory.get("unique_workload_records", 30),
            "native_text_records": source_inventory.get("native_extraction_statuses", {}).get("OK", 0),
            "encrypted_records": source_inventory.get("native_extraction_statuses", {}).get("ENCRYPTED", 0),
            "human_screening_completed": bool(source_boundary.get("human_screening_completed", False))
        },
        "screening_queue": {
            "status": queue_record.get("status", "NOT_RECORDED"),
            "records_ready": queue_inventory.get("acquired_records", 0),
            "expected_records": queue_inventory.get("expected_records", 30),
            "human_screening_completed": bool(queue_record.get("human_screening_completed", False))
        },
        "capabilities": {
            "workbook_check": True,
            "frame_check": True,
            "frozen_group_draw": True,
            "screening_source_queue": queue_record.get("status") == "SOURCE_QUEUE_READY",
            "workbook_write": False,
            "human_audit_credit": False,
            "research_pass": False
        },
        "limits": [
            "Browser requests use temporary files only and do not modify project research inputs.",
            "Workbook uploads are checked in a temporary directory and are not retained by the project.",
            "A frame check does not verify eligibility evidence, market coverage or audit status.",
            "A frozen draw does not make the research decision evaluable."
        ]
    }


def templates() -> dict[str, Any]:
    return {
        "candidate_frame_csv": read_text(ROOT / "pilot/templates/candidate-frame-template.csv", "matter_id,related_matter_group,eligibility_status,eligibility_reason\n"),
        "frozen_protocol_json": read_text(ROOT / "pilot/templates/frozen-protocol-template.json", "{\n  \"state\": \"DRAFT\"\n}\n"),
        "research_decision": "NOT_EVALUATED"
    }


def max_request_bytes(path: str) -> int:
    """Keep permitted workbook uploads separate from small JSON operations."""
    return MAX_WORKBOOK_REQUEST_BYTES if path == "/api/v1/workbook/check" else MAX_REQUEST_BYTES


def require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a nonempty string")
    return value


def optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when supplied")
    if len(value.encode("utf-8")) > MAX_AUXILIARY_TEXT_BYTES:
        raise ValueError(f"{key} exceeds the 2 MB local limit")
    return value


def parse_session_csv(text: str) -> set:
    """Mirror the CLI's narrow daily-session validation without retaining a file."""
    rows = csv.DictReader(StringIO(text, newline=""))
    if not rows.fieldnames or "date" not in rows.fieldnames:
        raise ValueError("sessions_csv requires a date column containing YYYY-MM-DD")
    dates = [day(row.get("date")) for row in rows]
    if not dates or any(value is None for value in dates) or len(set(dates)) != len(dates):
        raise ValueError("sessions_csv dates must be nonempty, valid and unique")
    return set(dates)


def parse_selection_manifest(text: str) -> list[str]:
    def no_duplicates(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"selection_manifest_json repeats JSON key: {key}")
            output[key] = value
        return output

    try:
        manifest = json.loads(text, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError("selection_manifest_json must be valid JSON") from exc
    ids = manifest.get("selected_matter_ids") if isinstance(manifest, dict) else None
    if not isinstance(ids, list) or not all(isinstance(value, str) for value in ids):
        raise ValueError("selection_manifest_json requires selected_matter_ids as a list of strings")
    return ids


def frame_check(payload: dict[str, Any]) -> dict[str, Any]:
    frame_csv = require_string(payload, "frame_csv")
    if len(frame_csv.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("frame_csv exceeds the local request limit")
    with tempfile.TemporaryDirectory(prefix="evidrava-frame-api-") as directory:
        frame_path = Path(directory) / "candidate-frame.csv"
        frame_path.write_text(frame_csv, encoding="utf-8", newline="")
        report = inspect_frame(frame_path)
    return {"report": report, "research_decision": "NOT_EVALUATED"}


def sample_draw(payload: dict[str, Any]) -> dict[str, Any]:
    frame_csv = require_string(payload, "frame_csv")
    protocol_json = require_string(payload, "protocol_json")
    if len(frame_csv.encode("utf-8")) + len(protocol_json.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("frame and protocol text exceed the local request limit")
    with tempfile.TemporaryDirectory(prefix="evidrava-draw-api-") as directory:
        frame_path = Path(directory) / "candidate-frame.csv"
        protocol_path = Path(directory) / "frozen-protocol.json"
        frame_path.write_text(frame_csv, encoding="utf-8", newline="")
        protocol_path.write_text(protocol_json, encoding="utf-8", newline="")
        report, selection_blob = draw_sample(frame_path, protocol_path)
    selection = json.loads(selection_blob.decode("utf-8"))
    return {"report": report, "selection_manifest": selection, "research_decision": "NOT_EVALUATED"}


def workbook_check(payload: dict[str, Any]) -> dict[str, Any]:
    """Check browser-supplied workbook bytes without retaining them in the project."""
    encoded = require_string(payload, "workbook_base64")
    if len(encoded.encode("utf-8")) > MAX_WORKBOOK_REQUEST_BYTES:
        raise ValueError("workbook_base64 exceeds the local request limit")
    try:
        blob = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise ValueError("workbook_base64 must be valid unwrapped Base64") from exc
    if not blob or len(blob) > MAX_WORKBOOK_BYTES:
        raise ValueError("Workbook exceeds the 20 MB pilot limit")
    sessions_csv = optional_string(payload, "sessions_csv")
    selection_manifest_json = optional_string(payload, "selection_manifest_json")
    additional_inputs = {}
    with tempfile.TemporaryDirectory(prefix="evidrava-workbook-api-") as directory:
        workbook_path = Path(directory) / "uploaded-registry.xlsx"
        workbook_path.write_bytes(blob)
        data = load_registry(workbook_path)
        if sessions_csv is not None:
            data["session_dates"] = parse_session_csv(sessions_csv)
            additional_inputs["sessions_sha256"] = sha256(sessions_csv.encode("utf-8")).hexdigest()
        if selection_manifest_json is not None:
            data["selected_matter_ids"] = parse_selection_manifest(selection_manifest_json)
            additional_inputs["selection_manifest_sha256"] = sha256(selection_manifest_json.encode("utf-8")).hexdigest()
        report = inspect_registry(data)
    report.update({
        "checker_version": __version__,
        "source_name": "browser-uploaded-workbook.xlsx",
        "workbook_sha256": data["workbook_sha256"],
        "contract_sha256": data["contract_sha256"],
        "additional_inputs": additional_inputs,
        "formula_calculation": "NOT_RUN",
        "supplied_workbook_suite": "NOT_RUN",
        "temporary_upload_only": True,
    })
    return {"report": report, "research_decision": "NOT_EVALUATED"}


def route_request(method: str, target: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    """Route a pre-parsed request, keeping HTTP handling separate from logic."""
    parsed = urlsplit(target)
    if parsed.query or parsed.fragment:
        return HTTPStatus.BAD_REQUEST, error_response("QUERY_NOT_ALLOWED", "This local API does not accept query parameters")
    path = parsed.path
    if method == "GET" and path == "/health":
        return HTTPStatus.OK, {"service": "evidrava-backend", "status": "ok", "version": __version__}
    if method == "GET" and path == "/api/v1/project-status":
        return HTTPStatus.OK, project_status()
    if method == "GET" and path == "/api/v1/templates":
        return HTTPStatus.OK, templates()
    if method == "POST" and path == "/api/v1/frame/check":
        try:
            return HTTPStatus.OK, frame_check(payload or {})
        except ValueError as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, error_response("FRAME_INVALID", str(exc))
    if method == "POST" and path == "/api/v1/workbook/check":
        try:
            return HTTPStatus.OK, workbook_check(payload or {})
        except (OSError, ValueError, KeyError, TypeError, BadZipFile, InvalidFileException, ParseError) as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, error_response("WORKBOOK_INVALID", str(exc))
    if method == "POST" and path == "/api/v1/sample/draw":
        try:
            return HTTPStatus.OK, sample_draw(payload or {})
        except ValueError as exc:
            return HTTPStatus.UNPROCESSABLE_ENTITY, error_response("DRAW_REJECTED", str(exc))
    return HTTPStatus.NOT_FOUND, error_response("ROUTE_NOT_FOUND", "The requested local API route is not available")


class BackendHandler(BaseHTTPRequestHandler):
    server_version = "EvidravaBackend/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        print(f"backend {self.address_string()} - {format % args}")

    def _write_json(self, status: int, body: dict[str, Any]) -> None:
        data = json_bytes(body)
        self.send_response(status)
        self.send_header("Content-Type", JSON_TYPE)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> tuple[dict[str, Any] | None, tuple[int, dict[str, Any]] | None]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return None, (HTTPStatus.UNSUPPORTED_MEDIA_TYPE, error_response("JSON_REQUIRED", "Use Content-Type: application/json"))
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError:
            return None, (HTTPStatus.LENGTH_REQUIRED, error_response("CONTENT_LENGTH_REQUIRED", "A valid Content-Length is required"))
        if length < 1 or length > max_request_bytes(urlsplit(self.path).path):
            return None, (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error_response("REQUEST_TOO_LARGE", "Request exceeds the local size limit"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, (HTTPStatus.BAD_REQUEST, error_response("INVALID_JSON", "Request body must be valid UTF-8 JSON"))
        if not isinstance(payload, dict):
            return None, (HTTPStatus.BAD_REQUEST, error_response("JSON_OBJECT_REQUIRED", "Request body must be a JSON object"))
        return payload, None

    def do_GET(self) -> None:
        status, body = route_request("GET", self.path)
        self._write_json(status, body)

    def do_POST(self) -> None:
        payload, error = self._read_json_body()
        if error is not None:
            self._write_json(*error)
            return
        status, body = route_request("POST", self.path, payload)
        self._write_json(status, body)

    def do_OPTIONS(self) -> None:
        self._write_json(HTTPStatus.METHOD_NOT_ALLOWED, error_response("METHOD_NOT_ALLOWED", "CORS preflight is handled by the local middleware"))

    def do_PUT(self) -> None:
        self._write_json(HTTPStatus.METHOD_NOT_ALLOWED, error_response("METHOD_NOT_ALLOWED", "Only GET and POST are supported"))

    do_DELETE = do_PUT
    do_PATCH = do_PUT


def create_server(host: str = "127.0.0.1", port: int = 8002) -> ThreadingHTTPServer:
    require_loopback_host(host)
    return ThreadingHTTPServer((host, port), BackendHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Evidrava backend API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args(argv)
    try:
        server = create_server(args.host, args.port)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Evidrava backend listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
