"""Command-line entry point for the bounded workbook pilot."""
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from . import __version__
from .checks import day, inspect_registry
from .report import render_html
from .workbook import load_registry, serial
from .screening import load_reference, read_csv, summarize_screening
from .screening_report import render_screening
from .sources import collect_sources


def read_sessions(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if not rows.fieldnames or "date" not in rows.fieldnames:
            raise ValueError("Session CSV requires a date column containing YYYY-MM-DD")
        dates = [day(row["date"]) for row in rows]
    if not dates or any(d is None for d in dates) or len(set(dates)) != len(dates):
        raise ValueError("Session dates must be nonempty, valid, unique dates")
    return set(dates)


def write_report(target, result, renderer=render_html, data_filename="validation.json", kind="preparation-check"):
    target = target.resolve()
    if target.exists():
        raise ValueError("Output exists; choose a new directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}-incomplete-", dir=target.parent))
    # Do not remove interrupted output. A final directory exists only on success.
    (temporary / data_filename).write_text(json.dumps(result, indent=2, default=serial, allow_nan=False) + "\n", encoding="utf-8")
    (temporary / "report.html").write_text(renderer(result), encoding="utf-8")
    manifest = {"kind": kind, "completed": True, "publication": "local_only",
                "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in temporary.iterdir()}}
    (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # os.rename refuses an existing destination on Windows; explicitly check on
    # other platforms as well. There is no recursive deletion or overwrite flag.
    if target.exists():
        raise ValueError("Output was created concurrently; incomplete output retained")
    os.rename(temporary, target)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="evidrava", description="Evidrava: prepare point-in-time market evidence. Local reports do not calculate Excel formulas or a research decision.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check-workbook", help="Read a v3.3 workbook without modifying it")
    check.add_argument("--workbook", type=Path, required=True)
    check.add_argument("--out", type=Path, required=True, help="New directory for JSON and HTML reports")
    check.add_argument("--sessions", type=Path, help="Verified venue session CSV with a date column; required if Snapshot B3 is populated")
    check.add_argument("--selection-manifest", type=Path, help="JSON with selected_matter_ids; required for a frozen workbook")
    screening = commands.add_parser("screening-report", help="Check the working 30-record CSV and summarize observed human workload offline")
    screening.add_argument("--csv", type=Path, required=True, help="Editable working copy of screening_30.csv")
    screening.add_argument("--reference", type=Path, default=Path("pilot/screening/screening_30.csv"), help="Preserved original beside its manifest and raw capture folder")
    screening.add_argument("--out", type=Path, required=True, help="New directory for screening.json, report.html and manifest.json")
    screening.add_argument("--candidate-listings", type=int, help="Optional illustrative initial-screening workload; withheld until all 30 records have complete timing observations")
    sources = commands.add_parser("collect-sources", help="Collect official PDFs and provisional page text for named reconnaissance records")
    sources.add_argument("--ids", nargs="+", required=True, help="Explicit original identifiers, for example RECON-01 RECON-02 RECON-03")
    sources.add_argument("--reference", type=Path, default=Path("pilot/screening/screening_30.csv"), help="Preserved original with its manifest and captures")
    sources.add_argument("--out", type=Path, required=True, help="New directory for source files, extraction and provenance")
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ValueError("Output exists; choose a new directory")
        if args.command == "collect-sources":
            reference, provenance = load_reference(args.reference)
            indexed = {r["screening_id"]: r for r in reference}
            if len(set(args.ids)) != len(args.ids) or any(sid not in indexed for sid in args.ids):
                raise ValueError("Source IDs must be distinct identifiers present in the original batch")
            result = collect_sources([indexed[sid] for sid in args.ids], args.out, reference_provenance=provenance)
            print(json.dumps({"output": str(args.out.resolve()), "status": result["status"], **result["counts"],
                              "human_screening_completed": False, "research_decision": "NOT_EVALUATED"}, indent=2))
            return 0 if result["status"] == "COMPLETE" else 3
        if args.command == "screening-report":
            reference, provenance = load_reference(args.reference)
            rows, digest = read_csv(args.csv)
            result = summarize_screening(rows, reference, args.candidate_listings)
            result.update({"checker_version": __version__, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                           "input_sha256": digest, "input_name": args.csv.name, "reference_provenance": provenance,
                           "python_version": sys.version.split()[0],
                           "checker_source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}})
            if sha256(args.csv.read_bytes()).hexdigest() != digest:
                raise ValueError("Working CSV changed during analysis; rerun against a stable copy")
            write_report(args.out, result, render_screening, "screening.json", "screening-workload")
            print(json.dumps({"output": str(args.out.resolve()), "status": result["status"],
                              "expected_records": result["summary"]["expected_records"],
                              "completed_attempts": result["summary"]["completed_screening_attempts"],
                              "complete_timing_observations": result["summary"]["complete_timing_observations"],
                              "research_decision": "NOT_EVALUATED"}, indent=2))
            return 3 if result["status"] == "INVALID" else 0
        data = load_registry(args.workbook)
        additional_inputs = {}
        if args.sessions:
            data["session_dates"] = read_sessions(args.sessions)
            additional_inputs["sessions_sha256"] = sha256(args.sessions.read_bytes()).hexdigest()
        if args.selection_manifest:
            manifest = json.loads(args.selection_manifest.read_text(encoding="utf-8-sig"))
            ids = manifest.get("selected_matter_ids")
            if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                raise ValueError("Selection manifest requires a selected_matter_ids list of strings")
            data["selected_matter_ids"] = ids
            additional_inputs["selection_manifest_sha256"] = sha256(args.selection_manifest.read_bytes()).hexdigest()
        result = inspect_registry(data)
        source_files = sorted(Path(__file__).parent.glob("*.py"))
        result.update({"checker_version": __version__, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                       "source_name": data["source_name"], "workbook_sha256": data["workbook_sha256"],
                       "contract_sha256": data["contract_sha256"], "additional_inputs": additional_inputs,
                       "checker_source_sha256": {p.name: sha256(p.read_bytes()).hexdigest() for p in source_files},
                       "python_version": sys.version.split()[0], "formula_calculation": "NOT_RUN",
                       "supplied_workbook_suite": "NOT_RUN"})
        if sha256(args.workbook.read_bytes()).hexdigest() != result["workbook_sha256"]:
            raise ValueError("Workbook changed during validation; rerun against a stable copy")
        write_report(args.out, result)
        print(json.dumps({"output": str(args.out.resolve()), "protocol_status": result["protocol_status"],
                          "validation_status": result["validation_status"], "research_decision": "NOT_EVALUATED",
                          "errors": sum(d["severity"] == "error" for d in result["diagnostics"]),
                          "warnings": sum(d["severity"] == "warning" for d in result["diagnostics"])}, indent=2))
        return 3 if result["validation_status"] == "INVALID" else 0
    except (OSError, ValueError, KeyError, TypeError, BadZipFile, InvalidFileException) as exc:
        print(f"Check could not complete: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
