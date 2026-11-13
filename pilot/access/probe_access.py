"""Fetch the four declared public daily archives once; retain metadata only."""
import csv
import datetime as dt
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_BYTES = 10 * 1024 * 1024


def probe(item):
    started = dt.datetime.now(dt.timezone.utc)
    clock = time.perf_counter()
    result = {**item, "started_at_utc": started.isoformat(), "http_status": None,
              "result": "NOT_COMPLETED", "raw_data_retained": False}
    try:
        req = urllib.request.Request(item["url"], headers={"User-Agent": "SEBI-research-feasibility-probe/0.1"})
        with urllib.request.urlopen(req, timeout=30) as response:
            result["http_status"] = response.status
            result["content_type"] = response.headers.get("Content-Type")
            result["final_url"] = response.geturl()
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Response exceeds the bounded probe size")
        result["download_bytes"] = len(raw)
        result["zip_sha256"] = hashlib.sha256(raw).hexdigest()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = [x for x in archive.infolist() if not x.is_dir()]
            if len(entries) != 1 or entries[0].file_size > 20 * 1024 * 1024:
                raise ValueError("Unexpected ZIP member count or uncompressed size")
            entry = entries[0]
            result["csv_member"] = entry.filename
            data = archive.read(entry)
        result["csv_sha256"] = hashlib.sha256(data).hexdigest()
        rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
        headers = list(rows[0]) if rows else []
        nonempty_headers = [h for h in headers if h]
        result["headers"] = nonempty_headers
        result["row_count_before_universe_filter"] = len(rows)
        isin_field = "ISIN"
        result["nonempty_isin_rows"] = sum(bool((r.get(isin_field) or "").strip()) for r in rows)
        result["distinct_nonempty_isins"] = len({r[isin_field].strip() for r in rows if (r.get(isin_field) or "").strip()})
        if item["format"] == "legacy":
            date_fields = ["TIMESTAMP"]
            required = ["SYMBOL", "SERIES", "OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "ISIN", "TIMESTAMP"]
            parse_date = lambda x: dt.datetime.strptime(x.strip(), "%d-%b-%Y").date().isoformat()
        else:
            date_fields = ["TradDt", "BizDt"]
            required = ["TradDt", "BizDt", "ISIN", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol"]
            parse_date = lambda x: dt.date.fromisoformat(x.strip()).isoformat()
        result["missing_required_headers"] = [x for x in required if x not in headers]
        date_values = {}
        for field in date_fields:
            values = sorted({parse_date(r[field]) for r in rows if (r.get(field) or "").strip()})
            date_values[field] = values
        result["observed_date_values"] = date_values
        result["dates_match_request"] = bool(rows) and all(values == [item["date"]] for values in date_values.values())
        result["result"] = "PARSED_AND_DATE_MATCHED" if not result["missing_required_headers"] and result["dates_match_request"] else "PARSED_WITH_MISMATCH"
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["result"] = "HTTP_ERROR"
        result["error"] = str(exc)
    except Exception as exc:
        result["result"] = "ERROR"
        result["error"] = type(exc).__name__ + ": " + str(exc)
    result["elapsed_seconds"] = round(time.perf_counter() - clock, 4)
    return result


def main():
    plan_bytes = (HERE / "probe_plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    assert len(plan["requests"]) == plan["max_daily_archive_requests"] == 4
    report_path = HERE / "probe_results_2026-11-07.json"
    if report_path.exists():
        raise SystemExit("Result already exists. Preserve it; choose a new dated run instead of overwriting.")
    report = {"plan_sha256": hashlib.sha256(plan_bytes).hexdigest(), "plan_date_local": plan["plan_date_local"],
              "timezone": plan["timezone"], "request_policy": "One sequential GET per planned daily file; no retries or bypass",
              "web_checks": [{"url": "https://www.nseindia.com/all-reports", "result": "Opened in web tool; legacy cash Bhavcopy discontinued 8 July 2024; UDiFF listed"},
                             {"url": "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx", "result": "Web tool returned 403 Forbidden; no bypass attempted"}],
              "probes": [], "limitations": ["Access/format checks only, not complete history or source-vintage verification.",
              "No per-episode warm-up, corporate-action, historical-identity or legal-evidence audit was performed.",
              "All row counts precede the cash-equity research universe filter.",
              "Public retrieval does not establish project-specific usage or redistribution permission.",
              "No raw market files or prices were retained."]}
    for n, item in enumerate(plan["requests"]):
        result = probe(item)
        report["probes"].append(result)
        print(json.dumps({k: result.get(k) for k in ["date","http_status","result","row_count_before_universe_filter","elapsed_seconds"]}), flush=True)
        if n + 1 < len(plan["requests"]):
            time.sleep(0.5)
    report["completed_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["total_download_bytes"] = sum(x.get("download_bytes", 0) for x in report["probes"])
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Saved metadata-only report: " + str(report_path), flush=True)


if __name__ == "__main__":
    main()
