"""Prepare the bounded 30-record reconnaissance batch; no research sample is drawn."""
import argparse
import csv
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pilot" / "screening"
RAW = OUT / "raw"
URL = "https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp"
REFERER = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9&smid=0"
STRATA = [(2011, 2015), (2016, 2020), (2021, 2025)]


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.cells = None
        self.cell = None
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.cells, self.href = [], None
        elif tag == "td" and self.cells is not None:
            self.cell = []
        elif tag == "a" and self.cell is not None:
            href = dict(attrs).get("href", "")
            if urlparse(href).netloc == "www.sebi.gov.in" and self.href is None:
                self.href = href

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.cells.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.cells is not None:
            if len(self.cells) == 2 and self.href:
                self.rows.append({"listing_date": datetime.strptime(self.cells[0], "%b %d, %Y").date().isoformat(),
                                  "title": self.cells[1], "url": self.href})
            self.cells, self.cell = None, None


def params_for(start, end, page):
    return dict(nextValue="1", next="s" if page == 0 else "n", search="",
                fromDate=f"01-01-{start}", toDate=f"31-12-{end}", fromYear="", toYear="",
                deptId="-1", sid="2", ssid="9", smid="0", ssidhidden="9", intmid="-1",
                sText="Enforcement", ssText="Orders", smText="-- All Sub Section List --",
                doDirect="-1" if page == 0 else str(page))


def get_page(start, end, page, fetch_missing):
    stem = f"{start}-{end}_page_{page}"
    path, meta_path = RAW / f"{stem}.html", RAW / f"{stem}.request.json"
    params = params_for(start, end, page)
    if not path.exists():
        if not fetch_missing:
            raise RuntimeError(f"Missing cached response {path.name}; use --fetch-missing explicitly.")
        time.sleep(0.5)
        before = time.perf_counter()
        retrieved_at = datetime.now(timezone.utc).isoformat()
        req = Request(URL, data=urlencode(params).encode(), headers={"Content-Type": "application/x-www-form-urlencoded",
                      "Referer": REFERER, "User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=30) as response:
            body, status = response.read(), response.status
        elapsed = time.perf_counter() - before
        path.write_bytes(body)
        meta_path.write_text(json.dumps({"parameters": params, "status": status, "retrieved_at_utc": retrieved_at,
                                        "elapsed_seconds": elapsed, "sha256": hashlib.sha256(body).hexdigest()}, indent=2), encoding="utf-8")
    body, meta = path.read_bytes(), json.loads(meta_path.read_text(encoding="utf-8"))
    if meta["parameters"] != params or meta["sha256"] != hashlib.sha256(body).hexdigest():
        raise RuntimeError(f"Cached request/byte mismatch: {stem}")
    if "retrieved_at_utc" not in meta:
        # The first probe was saved before adding an explicit clock field.
        meta["retrieved_at_utc"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        meta["retrieval_time_basis"] = "raw-response file modification time; approximate completion time"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    text = body.decode("utf-8")
    found = re.search(r"([\d,]+) to ([\d,]+) of ([\d,]+) records", text)
    if not found:
        raise RuntimeError(f"No pagination control: {stem}")
    first, last, total = [int(x.replace(",", "")) for x in found.groups()]
    parser = Rows(); parser.feed(text)
    if len(parser.rows) != last - first + 1 or first != page * 25 + 1:
        raise RuntimeError(f"Unexpected pagination/row count: {stem}")
    if any(not f"{start}-01-01" <= x["listing_date"] <= f"{end}-12-31" for x in parser.rows):
        raise RuntimeError(f"Date filter failure: {stem}")
    return parser.rows, {"raw_path": f"raw/{path.name}", "request_path": f"raw/{meta_path.name}", "url": URL,
                         **meta, "page_index": page, "first_record": first, "last_record": last, "total_records": total}


def triage(title):
    if re.search(r"\bRTI\b|right to information|appellate authority.*information", title, re.I):
        return "provisional_exclude_administrative", "Title explicitly identifies RTI/information administration; confirm during human screening."
    if re.search(r"non.redressal of investor grievance", title, re.I):
        return "provisional_exclude_nontrading", "Title explicitly identifies non-redressal of investor grievances; confirm the document has no separate eligible trading conduct."
    if re.search(r"manipulat|wash trad|circular trad|front.?running|spoof|price.?rig|volume.?rig", title, re.I):
        return "candidate_for_document_review", "Title signals a potentially relevant trading allegation; eligibility, cash-equity scope and matter identity remain unverified."
    return "uncertain_requires_document_review", "Title alone does not establish conduct, instrument eligibility or predecessor/group relationships."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-missing", action="store_true")
    ap.add_argument("--verify-existing", action="store_true", help="Check fixed selection fields without overwriting human edits or making requests.")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    output = OUT / "screening_30.csv"
    if args.verify_existing and args.fetch_missing:
        raise RuntimeError("Verification is offline; do not combine with --fetch-missing.")
    if output.exists() and not args.verify_existing:
        raise RuntimeError("screening_30.csv already exists; preserve human edits. Use the retained files for review.")
    batch, requests = [], []
    for start, end in STRATA:
        first_rows, first_meta = get_page(start, end, 0, args.fetch_missing)
        total = first_meta["total_records"]
        last_page = math.ceil(total / 25) - 1
        pages = [0, last_page // 2, last_page]
        if len(set(pages)) != 3:
            raise RuntimeError("Too few pages for prespecified design; do not improvise a different selection.")
        for page in pages:
            rows, meta = (first_rows, first_meta) if page == 0 else get_page(start, end, page, args.fetch_missing)
            if meta["total_records"] != total:
                raise RuntimeError("Listing total changed within stratum; retain raw responses and resolve before selecting.")
            requests.append(meta)
            positions = [1, 9, 17, 25] if page == 0 else [1, (len(rows) + 1) // 2, len(rows)]
            for position in positions:
                row = rows[position - 1]
                status, reason = triage(row["title"])
                listing_id_match = re.search(r"_(\d+)\.html", row["url"])
                batch.append({"screening_id": f"RECON-{len(batch)+1:02d}", "listing_date_stratum": f"{start}-{end}",
                              "page_index_zero_based": page, "row_in_page_one_based": position,
                              "listing_record_position": meta["first_record"] + position - 1, **row,
                              "official_listing_id": listing_id_match.group(1) if listing_id_match else "",
                              "response_sha256": meta["sha256"], "machine_title_triage": status,
                              "machine_title_reason": reason, "human_reviewer_id": "", "human_screening_decision": "",
                              "human_decision_reason": "", "document_opened": "", "eligibility_source_locator": "",
                              "cash_equity_scope": "", "group_key_or_uncertain": "", "predecessor_search_status": "",
                              "predecessor_evidence": "", "screening_active_minutes": "", "grouping_active_minutes": "",
                              "predecessor_active_minutes": "", "access_wait_minutes": "", "followup_needed": "", "notes": ""})
    assert len(batch) == 30 and len({r["url"] for r in batch}) == 30
    if args.verify_existing:
        with output.open(encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
        assert len(existing) == len(batch)
        immutable = list(batch[0])[:list(batch[0]).index("human_reviewer_id")]
        for expected, actual in zip(batch, existing):
            for key in immutable:
                assert str(expected[key]) == actual[key], (expected["screening_id"], key)
        print("Verified 30 fixed selections and machine-triage fields against cached responses; human edits untouched; no network requests.")
        return
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(batch[0])); writer.writeheader(); writer.writerows(batch)
    manifest = {"observed_on_client_date": "2026-11-07", "purpose": "workload reconnaissance; not the research sample",
                "selection_rule": "10 per listing-date interval: first, floor(last_page/2), last page; rows 1/9/17/25 on first page and first/middle/last on each other page. No title/keyword-dependent selection.",
                "rule_timing_note": "The first 2011-2015 page was inspected while confirming parsing; positional rule fixed before the remaining eight requests. This is not preregistration or random sampling.",
                "batch_rows": 30, "direct_listing_requests": len(requests), "source": REFERER,
                "machine_request_seconds_sum": sum(r["elapsed_seconds"] for r in requests),
                "machine_title_triage": "Deterministic pattern rule in script; no PDFs or substantive legal eligibility review.",
                "human_screening_completed": False, "human_throughput_estimate": None,
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "screening_csv_initial_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "requests": requests}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"rows": len(batch), "listing_requests": len(requests),
                      "stratum_totals": {f"{a}-{b}": requests[i*3]["total_records"] for i,(a,b) in enumerate(STRATA)},
                      "title_triage": {k: sum(r["machine_title_triage"] == k for r in batch) for k in sorted({r["machine_title_triage"] for r in batch})},
                      "machine_request_seconds_sum": manifest["machine_request_seconds_sum"], "human_timing": "not measured"}, indent=2))


if __name__ == "__main__":
    main()
