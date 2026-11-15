# Data and Feasibility

These records describe Evidrava source access and preparation observed on 4–15 November 2026 in Asia/Kolkata. Individual observations retain their dates. The frame scope, case-specific data coverage and independent review capacity remain open. The active work order and checkpoints are in the [pilot plan](pilot-plan.md).

## Implementation update: 14 November

Workbook v3.3 and proposal v2.4 are now the accepted working references. Their source bytes and the supplied 114-scenario suite are preserved in the [received release](../references/incoming/2026-11-13/receipt.json). The supplied LibreOffice report records 114 passes and the new mutation report records 11 catches. These are author-run results; local native recalculation and Excel compatibility remain unverified.

Evidrava 0.7.2 provides preparation checking, screening-workload reporting, a hash-checked source navigation queue, official-source collection, a provisional review brief, bounded candidate-frame preparation and a local browser console with temporary workbook checks while reviewer search continues. Missing reviewer sign-offs receive no audit credit. Official source packets for all 30 fixed-workload records are now preserved; machine-assisted notes exist only for the first three. Earlier archive counts and market-data probes were not refreshed. No case-specific market coverage, human screening time, frozen candidate frame or research draw has been established. [Run the commands](../README.md#run-the-project)

## Source-preparation update: 16 November

The fixed 30-record workload batch now has 30 acquired official-source records across a [first-three packet](../pilot/sources/recon-first-three/report.html), a [remaining-record packet](../pilot/sources/recon-remaining-2026-11-16/report.html), and a [retry packet](../pilot/sources/recon-retry-2026-11-16/report.html). Twenty-nine documents have native extracted text; RECON-08 is encrypted and remains explicitly textless. The [source-preparation record](../pilot/development/evidrava-source-preparation-2026-11-16.json) pins all packet manifests and records one rejected external appeal link beside RECON-16's official SEBI order. These facts do not establish eligibility, publication date, legal scope or human review.

The [screening source queue](../pilot/development/evidrava-screening-queue-v0.7.1-2026-11-16/report.html) verifies the stored packet hashes before linking every fixed workload record to its original PDF, page text and page inventory. It is a read-only navigation aid, not a completed screening exercise: it does not insert a decision, timing value, reviewer name or audit outcome. RECON-08 remains visible as an encrypted source that requires a legitimate manual inspection route. Keep the queue and source packets on the same filesystem volume so its relative links remain portable.

## First three source packets

On 13 November, `collect-sources` retrieved the official listing page and PDF for each of RECON-01, RECON-02 and RECON-03. All three downloads completed and pypdf 6.21.4 returned native text with extraction status OK. Page counts describe PDF positions, not independently verified printed page labels.

| Workload ID | PDF pages | PDF bytes |
| --- | ---: | ---: |
| RECON-01 | 5 | 222,957 |
| RECON-02 | 32 | 450,063 |
| RECON-03 | 20 | 422,071 |

The [review index](../pilot/sources/recon-first-three/report.html) links original PDFs and page-labelled text. The [manifest](../pilot/sources/recon-first-three/manifest.json) preserves official URLs, response hashes, retrieval metadata and extraction outcomes. The packets contain no human screening decision, reviewer sign-off or verified publication date. They are three records from the positional workload exercise, not three selected or eligible research matters.

Start measured screening with these documents, recording actual human time in `working/screening_30.csv`. Inspect the original pages, document scope and possible related proceedings, and follow predecessor references before deciding include, exclude or uncertain. Native text can miss layout, scans or tables and is a navigation aid. Independent audit can follow when a reviewer becomes available.

To collect another explicit batch, use a new output directory:

```text
python -m evidrava collect-sources --ids RECON-04 RECON-05 --out runs/sources-next
```

The collector verifies the preserved batch before network access and accepts only official SEBI HTTPS sources. Ambiguous links and failures stay visible; it does not choose the first of several PDFs or overwrite an earlier packet. [Limits and status meanings](technical-reference.md#source-collection-command)

## Provisional screening findings: 14 November

The [brief](../pilot/screening/brief-first-three/report.html) brings together three machine-assisted records, 15 page anchors and open questions from the [notes](../pilot/screening/provisional-first-three-2026-11-14.json). Suggestions below are not human screening decisions or audited labels. All three records remain **PENDING_HUMAN_REVIEW** and stay in the 30-record workload exercise.

| Record | Provisional suggestion and source basis | Next verification |
| --- | --- | --- |
| RECON-01: Amrapali Films | Exclusion candidate: the order concerns SCORES authentication compliance, not a documented trading-manipulation episode (PDF p3, paras8–10). | Confirm the eventual compliance-only exclusion rule and record the actual human decision and effort. [Source](../pilot/sources/recon-first-three/records/RECON-01/source.pdf#page=3) |
| RECON-02: Home Trade | Uncertain: the order reports earlier website publication of SCNs (p6, para6), and names Pune/Bangalore exchanges (p2, para1). Its 2015 signature does not establish first disclosure. | Retrieve predecessors, verify episode-specific public dates and test historical venue coverage. Existing NSE probes do not establish Pune/Bangalore coverage. [Source](../pilot/sources/recon-first-three/records/RECON-02/source.pdf#page=6) |
| RECON-03: Khandwala / DSQ Biotech | Uncertain: the order describes 1999–2001 trading and a 2005 enquiry (pp1–2). Its final sanction is a warning (p19, paras20–22), not the earlier recommended suspension. | Verify prior public DSQ sources, historical instrument identity and conduct/warm-up coverage; preserve separate allegations, findings and final disposition. [Source](../pilot/sources/recon-first-three/records/RECON-03/source.pdf#page=19) |

`review-brief` confirms fingerprints, page references and exact anchor matches after whitespace normalization. It does not validate these interpretations, verify publication dates or settle eligibility. Human review must inspect the original pages and the surrounding context. The command writes only a new derived brief and leaves the working CSV unchanged. [Command and checks](technical-reference.md#provisional-review-brief-command) · [Application test run](../pilot/development/evidrava-increment-2026-11-15.json) · [Subsequent predecessor capture](../pilot/development/evidrava-predecessors-2026-11-15.json)

## Predecessor source review: 15 November

The bounded [capture helper](../scripts/capture_predecessors.py) saved eight planned official SEBI sources and two focused supplements. All ten responses were HTTP 200; the three PDFs yielded 13, 11 and 48 pages for the supplemental Home Trade, PPTL and DSQ group orders. Original bytes, response hashes, capture times and extracted text are preserved in the [main packet](../pilot/sources/predecessors-2026-11-15/report.html), [Home Trade supplement](../pilot/sources/predecessors-supplement-2026-11-15/report.html) and [date supplement](../pilot/sources/predecessors-date-supplement-2026-11-15/report.html). The [provisional review](../pilot/screening/predecessor-review-2026-11-15.html) records source scope and unresolved leads. Captures did not fill the working screening CSV or workbook.

| Matter | Earlier-source observations | What remains unresolved |
| --- | --- | --- |
| RECON-02: Home Trade | SEBI's 2006 M's Securities release displays 15 September while the linked order is dated 14 September. The order describes HTL broker activity in 1999–2001, but finds insufficient evidence of a FUTP violation by that broker. A separate Indavara order signed 25 September 2006 recounts HTL activity and a circular-trading allegation, then censures KYC/diligence failures. | Retrieve the 2008/2009 website notices and the 16 February 2006 director order cited in the 2015 order. Match each disclosure passage to the defined episode; do not infer public time from the order signature. |
| RECON-03: Khandwala / DSQ Biotech | The 2006 CSFB order page displays 27 November; its release page displays 29 November and its release body 28 November. The order covers DSQ trading in 1999–2001 and refers to earlier 2002 and 2003 SEBI orders. A 2007 PPTL summons order records Khandwala cross-deals during 21 February–22 March 2000. A 2009 DSQ company/group order identifies Khandwala transactions. | Retrieve the 2002 and 2003 orders named in the 2006 order. Keep the CSFB broker, PPTL proceeding, DSQ group parties and Khandwala respondent scope separate. The 2003 BKG order concerns a different DSQ period, 1994–1996. |

Under the draft 2011–2025 first-disclosure window, these records create a substantial pre-2011 eligibility concern. They do not establish the earliest episode-specific public disclosure. Page dates, order dates and retrieval timestamps remain distinct; exact publication dates, human screening, independent audit and episode linkage are not verified. Both records remain **PENDING_HUMAN_REVIEW**, first-disclosure dates remain unset and no episode has been granted strict usable credit. [Machine-readable review and capture hashes](../pilot/screening/predecessor-review-2026-11-15.json) · [Capture procedure](technical-reference.md#bounded-predecessor-capture)

## SEBI archive and candidate frame

On 5 November the All Orders query showed **21,837 listings across 874 pages** for 2011–2025. A listing is a document record. Eligible matter counts require screening, grouping and evidence of first public disclosure. [SEBI Orders archive](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9&smid=0)

| Listing-date interval | Records | Pages |
| --- | ---: | ---: |
| 2011–2015 | 5,919 | 237 |
| 2016–2020 | 7,424 | 297 |
| 2021–2025 | 8,494 | 340 |
| All Orders, 2011–2025 | 21,837 | 874 |
| Predecessor probe, 1900–2010 | 8,266 | 331 |

The 11 visible category queries summed to **21,788**, 49 below All Orders. Overlap, legacy classifications and filter behavior remain possible explanations. Reconcile category membership by row ID or official URL. The first SAT results page was headed by 6 July 2015 despite the 2025 query endpoint. Later appeal coverage needs separate verification.

| Category | `smid` | Listings |
| --- | ---: | ---: |
| SAT | 1 | 874 |
| Chairperson or members | 2 | 3,876 |
| Board settlements | 3 | 1,145 |
| Tribunal or court settlements | 146 | 0 returned |
| RTI appellate authority | 4 | 5,240 |
| Corporatisation or demutualisation | 5 | 0 returned |
| Adjudicating officer | 6 | 9,216 |
| Courts | 7 | 942 |
| Special courts | 77 | 86 |
| ED or CGM quasi-judicial orders | 133 | 395 |
| Regulation 30A intermediary orders | 138 | 14 |

### Reproduce the listing checks

The listing uses a form-encoded POST to `https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp` with the archive URL as Referer. The response contains listing and pagination HTML, followed by `#@#` and breadcrumb HTML. Start with the captured parameters and set `fromDate=01-01-2011`, `toDate=31-12-2025` for the full interval. The initial request uses `nextValue=1`, `next=s`, `doDirect=-1` and `smid=0`. Using `smid=-1` produced the same first response. [Captured request](../pilot/screening/raw/2011-2015_page_0.request.json) · [SEBI listing script](https://www.sebi.gov.in/js/entry.js)

For pagination, keep `nextValue=1`, set `next=n`, and use the zero-based page index in `doDirect`. Index 1 returned rows 26–50. Index 873 returned rows 21,826–21,837. Setting both dates to `03-01-2011` returned eight records from that date. A request with only `toDate=31-12-2010` returned 31,052 records headed by November 2026 entries. Adding the broad lower bound `fromDate=01-01-1900` produced the 8,266-record predecessor result. Always supply both bounds and validate row dates. The unfiltered page showed 31,052 records on 4 November and 31,051 during the 5 November session, so archive counts need timestamped reconciliation.

The 5 November reconnaissance used 27 direct HTTP requests, all HTTP 200, plus one web-tool open. A batch of 17 count and pagination queries took 3.373 seconds with at most two concurrent requests. The three final controls took 0.722 seconds. End-to-end collection and human review remain unmeasured. Raw response bytes were inspected in memory. Selected SHA-256 fingerprints record the historical responses.

| Response | SHA-256 |
| --- | --- |
| 2011–2025 first page | `cb736a8beaeeca8677adceefd45d7cfeaadecbf61d8faa2200b97da01a373650` |
| 2011–2025 page 2 | `933e3017fa6cfa9af3398d7e04d70b5abdd68ab7ef92ed82f902c93b6728dd01` |
| 2011–2025 last page | `de8e15a07d8d8226038db95e0d00fb65a3787268f65891a6d47afb407f3f3a45` |
| 1900–2010 first page | `71eed8d32d00d01da43013d044b8a51c33d1f42cd471fc27a5b249a564346f37` |
| 3 January 2011 control | `265b77b719e8521e5b8e77ee0b3734092e3d7d9595eb7675440aa861f18a5ad5` |

When building a frame, capture parameters, timestamps, hashes, page totals and official IDs or URLs. Reconcile skipped or duplicated pages, category discrepancies and changing totals. Review unclear titles with source documents. Use names and aliases to find possible links, then document each merge or split with evidence. Search referenced predecessors, including pre-2011 records, before assigning first-disclosure strata. Track later legal events separately through the observation cutoff. Archive the reconciled candidate frame, exclusions, merge map and selection settings before drawing matters. [Research method](research-method.md)

## Screening and timing

The **30-record workload exercise** prepared on 7 November uses ten unique URLs from each listing-date interval, spread across its first, middle and last pages. The first page was inspected to confirm parsing before the positional rule was fixed for the remaining requests. Nine requests succeeded and took about 5 seconds in total. That duration measures machine retrieval. Human screening times are blank. Title triage flagged one likely nontrading grievance and left 29 uncertain. The exercise is separate from the eventual research draw and supports workload planning. [Screening CSV](../pilot/screening/screening_30.csv) · [Selection manifest and capture hashes](../pilot/screening/manifest.json)

Before a screening batch, generate a fresh queue with `python -m evidrava screening-queue --out runs/screening-queue-01` and open its HTML report. The queue source links are checked against the packet manifest; nevertheless, a person must inspect the original document and retain the actual decision and effort only in the separate working CSV.

1. Save a dated copy of the CSV for human entries. Open each source and record the decision, reason, evidence locator, cash-equity scope, possible group and predecessor status. Keep unresolved records visible. Some listings link directly to a PDF. Retain the official URL when the numeric listing ID is blank.
2. Record active minutes for screening, grouping and predecessor search separately. Use the waiting-time column for download or access delays.
3. Summarize the completed count, total active minutes, median, range and unresolved follow-ups by interval. Compare proposed scopes using the measured work and explicit assumptions. The small positional batch supports a capacity check, while eligible-matter prevalence requires an appropriate sampling design.

Verify the original selection and cached responses from the project root. The verifier works offline and preserves human edits. The builder rejects attempts to overwrite the CSV. Its `--fetch-missing` option retrieves missing bounded pages. [Screening helper](../scripts/prepare_screening_batch.py)

```text
python scripts/prepare_screening_batch.py --verify-existing
```

### Recording the screening exercise

Use the separate working copy `working/screening_30.csv`. The first 12 columns are preserved source metadata and machine triage. The remaining columns record the actual person's work; automated title triage never substitutes for those entries. In this CSV, `human_reviewer_id` identifies the first screener, who may be the project lead. It does not attest to a second independent audit.

| Fields | Entry rule |
| --- | --- |
| `human_reviewer_id`, `human_decision_reason` | Actual screener identity and a source-based explanation. |
| `human_screening_decision` | `include`, `exclude` or `uncertain` (case-insensitive). Inclusion is a screening disposition, not a research-sample draw. |
| `document_opened`, `eligibility_source_locator` | `yes`/`no`, plus the page/paragraph or comparable source locator supporting include/exclude. An inaccessible source remains uncertain. |
| `cash_equity_scope` | `yes`, `no` or `uncertain`. Inclusion requires `yes`. |
| `group_key_or_uncertain` | Proposed group key, `uncertain`, or explicit `not_applicable` where justified. |
| `predecessor_search_status`, `predecessor_evidence` | `not_started`, `in_progress`, `complete`, `not_applicable` or `uncertain`. A complete search needs a recorded evidence trail, including a justified no-predecessor finding. |
| `screening_active_minutes`, `grouping_active_minutes`, `predecessor_active_minutes` | Actual nonnegative minutes for distinct activities. Avoid double-counting. Blank means unmeasured; zero means observed zero. |
| `access_wait_minutes` | Waiting measured separately; never added to active-work statistics. |
| `followup_needed`, `notes` | `yes`/`no` and useful context. Uncertain decisions or unfinished grouping/predecessor work need follow-up. |

Run the new command after entering a batch of observations:

```text
python -m evidrava screening-report --csv working/screening_30.csv --out runs/screening-01
```

It checks the unchanged original CSV fingerprint, preparer fingerprint, nine raw responses and request parameters without network access or metadata backfilling. It compares the working copy by ID, allows row sorting, and rejects additions, deletions, duplicate IDs, changed fixed fields or invalid timings. Previous outputs are preserved; use a new output directory each time.

The report separates a completed screening attempt from a complete timed observation and an unresolved follow-up. An uncertain attempt may be fully recorded and timed. Only valid completed attempts with all three active-minute fields enter the complete-time mean, median and range. Partial measured effort is retained separately as logged effort. Waiting has its own observation count. Empty cohorts have unavailable statistics rather than zero.

The optional `--candidate-listings` planning scenario is withheld until every original record has a complete valid timing observation. Its estimate is initial-screening hours under the explicit assumption of the same listing mix and effort; subsequent follow-up, annotation, audit and linkage remain additional. This positional batch cannot establish eligible-matter prevalence or a population-wide workload estimate. The [current progress report](../pilot/development/evidrava-screening/report.html) retains all 30 records as pending.

## Market-data access

On 7 November four predefined NSE cash-market ZIPs returned HTTP 200. Every file parsed, its data date matched the request, and the price, volume and identity headers were present. All rows contained ISINs. These row counts precede research universe filtering. The compressed responses totaled 394,383 bytes and were processed in memory. [Probe plan](../pilot/access/probe_plan.json) · [URLs, headers, hashes and timings](../pilot/access/probe_results_2026-11-07.json) · [Probe helper](../pilot/access/probe_access.py)

| Date | Format | Rows |
| --- | --- | ---: |
| 2 January 2012 | Legacy cash Bhavcopy | 1,526 |
| 2 January 2020 | Legacy cash Bhavcopy | 1,956 |
| 2 January 2024 | Legacy cash Bhavcopy | 2,658 |
| 2 January 2025 | UDiFF cash Bhavcopy | 2,930 |

The NSE reports page identified an 8 July 2024 legacy-to-UDiFF transition. Validate field meaning, units and series in both formats. The tested BSE routes returned HTTP 403 through the web reader on 4 and 7 November. A working no-cost BSE route remains to be established. Continuous history, vintage, delisted identities, corporate actions, calendar amendments and per-case conduct and warm-up coverage require separate checks. [NSE reports](https://www.nseindia.com/all-reports) · [BSE historical prices](https://www.bseindia.com/markets/equity/EQReports/StockPrcHistori.aspx?flag=0) · [BSE Bhavcopy](https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx) · [SEBI source directory](https://www.sebi.gov.in/curation/equity_cash_market.html)

The 4 November UDiFF probe of 2 January 2025 returned HTTP 200 and recorded the same 171,515 bytes, 2,930 rows and ZIP SHA-256 as the 7 November check. The other 4 November observations are below.

| Source | Observed result |
| --- | --- |
| [SEBI order PDF](https://www.sebi.gov.in/sebi_data/attachdocs/nov-2026/ORDER_1793768725.pdf) | Direct HTTP 200 after the web reader failed. The 562,432-byte file had 26 pages and readable first-page text. SHA-256 `629ceb87065451152ec8f87be206d678926f4bf989a8f613a068135712351bd8`. |
| [NSE legacy ZIP, 2 January 2015](https://nsearchives.nseindia.com/content/historical/EQUITIES/2015/JAN/cm02JAN2015bhav.csv.zip) | HTTP 200, 58,101 bytes and 1,605 rows. Date, OHLC, volume and ISIN checked. SHA-256 `92a0d43e883be89b86e36ce6a81c56d96a3b5faeaca698565736954a1058b9bd`. |
| [Equity master](https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv), [name changes](https://nsearchives.nseindia.com/content/equities/namechange.csv), [symbol changes](https://nsearchives.nseindia.com/content/equities/symbolchange.csv) | HTTP 200 with 2,627, 2,344 and 1,080 rows respectively. The master records listing date, symbol, series and ISIN. Change histories include effective dates. |
| [Corporate actions, 1–2 January 2025](https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-2025&to_date=02-01-2025) | HTTP 200, one event with ISIN, ex-date and broadcast-date fields. |
| [Trading holidays](https://www.nseindia.com/api/holiday-master?type=trading), [2015 cash-market calendar](https://nsearchives.nseindia.com/content/circulars/CMTR28337.pdf), [2025 cash-market calendar](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf) | Holiday API returned capital-market data and historical calendar circulars were readable. |

The 4 November source review recorded a possible no-cost NSE research route up to an aggregate 2 GB, subject to affiliation and use conditions. The recorded terms exclude commercial, speculative and investigative use and may require institutional formalities. Confirm applicable terms before bulk collection, track transfer volume and record redistribution permissions before release. The project uses a ₹0 budget. [NSE disclaimer](https://www.nseindia.com/static/nse-disclaimer) · [NSE data policy](https://www.nseindia.com/static/market-data/nse-data-policy) · [Research request form](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20Seeking%20Request%20Form-20250319.pdf) · [Data inventory](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Data%20list%20under%20NSE%20Data%20Sharing%20Policy%20for%20Research%20and%20Analysis_20250728.pdf)

## Workload and local resources

The 4 November machine check observed about 31.7 GiB RAM, 12 logical processors and 91.3 GiB free on the workspace drive. Use measured memory and storage when sizing a larger batch. Across 21,837 listings, hypothetical screening at 0.5, 1 and 2 minutes per listing would take about 182, 364 and 728 hours respectively, before document review, grouping, predecessor checks, annotation or audit. Measure the small exercise before committing to an archive-wide scope.

Estimate lead and auditor person-hours separately. Use counts from the candidate frame and first five selected matters. Record overlapping work once.

```text
frame hours = (candidate count × screening minutes + order count × grouping minutes
               + retrieval and reconciliation minutes) / 60
annotation hours = (matter count × setup minutes + order count × extraction minutes
                    + episode count × linkage minutes + slot count × claim review minutes) / 60
audit hours = (slot count × audit minutes + disagreement count × adjudication minutes) / 60
```

## Historical input fingerprints

These SHA-256 values were recorded during the 1 and 4 November reviews. The current workbook and proposal provenance is in the [technical reference](technical-reference.md).

| Historical input | SHA-256 |
| --- | --- |
| `SEBI_Episode_Registry_Template.xlsx` | `8e2e3cc2c5f0107f45946b290b8bb6386574a4ecc9ce5529216dbf2b3d18f68f` |
| `Research_Proposal_SEBI_Point_in_Time_Benchmark.docx` | `56af4148e739aea6fa5a5884eb0e927f5f10c6ff1ba9290f34646cdca7bd8a1b` |
| `SEBI_Episode_Registry_PreRegistration_Draft.xlsx` | `035fb6b98afbb0f5f6c74da4a2ef2d3186146308b11291e6d052a7210c6fb831` |
| `Research_Proposal_v2_DRAFT_SEBI_Point_in_Time_Benchmark.docx` | `a5e76f2bcf957352969fa6a06f28302890d32bb9c6706430e415b9f188266afc` |
| `SEBI_Episode_Registry_v2.xlsx` | `579d1fda9e1af4ad088db77bef6b7ac3d29b92a97417d51ed53aa96feba14ccc` |

The earlier review recorded these pointers for future literature and source checks. [indic-reg-bench](https://huggingface.co/datasets/siddharthgaur/indic-reg-bench) · [ADMA21](https://github.com/zhuye88/ADMA21) · [ADMA21 data description](https://github.com/zhuye88/ADMA21/blob/main/data.md) · [Options study](https://arxiv.org/abs/2608.05373) · [AuditFraudBench](https://arxiv.org/abs/2606.08345)
