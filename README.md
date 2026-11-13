# Evidrava

**A Point-in-Time Market Evidence Benchmark**

**Evidrava** is the finalized project name. The current local software version is **0.3.0**. This is an independent research project using public SEBI sources, with no claim of regulatory affiliation.

Evidrava builds a fair historical test for trading-anomaly detectors using public orders from the Securities and Exchange Board of India (SEBI). An order may describe conduct years after it happened. A model tested on 2019 data must not receive facts that first became public in 2024. Otherwise it has effectively seen the answers before the exam. This is **hindsight leakage**.

The registry records alleged or documented conduct, supporting passages and legal status. An order does not automatically establish wrongdoing by every named person or on every trading day. The project measures what public daily data and properly timed labels can support. [Research proposal v2.4](references/incoming/2026-11-13/Research_Proposal_v2.4_DRAFT_SEBI_Point_in_Time_Benchmark.docx)

## What we are building

| Part | Purpose | Available now |
| --- | --- | --- |
| Registry | Connect matters, instrument-specific episodes, order pages, public dates, label versions and human reviews. | [Workbook v3.3](references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx) |
| Preparation checker | Detect structural/evidence problems, count outstanding review obligations and write a local report. | [Python implementation](evidrava/) and [local tests](tests/test_checker.py) |
| Screening workload | Track the fixed 30-record exercise, complete timings, missing fields and unresolved follow-ups. | [Screening report](pilot/development/evidrava-screening/report.html) and [screening tests](tests/test_screening.py) |
| Source collection | Save official documents, byte hashes and provisional text labelled by PDF page. | [First three source packets](pilot/sources/recon-first-three/report.html) and [acquisition tests](tests/test_sources.py) |
| Workbook regression suite | Populate synthetic cases and check formula results using LibreOffice. | [114 supplied scenarios](references/incoming/2026-11-13/registry_tests_v33/README.md); the author's run passed, local recalculation pending. |
| Research protocol | Define sampling, timing, audit, evaluation and the feasibility decision. | [Research Method](docs/research-method.md) and the draft proposal. |

A **matter** is an underlying proceeding that may have several orders. An **episode** identifies an instrument and conduct interval. Related matters share a group for independence counts and evaluation splits. Source publication, model availability and the date a person audited the evidence are separate facts.

## Current status

**Development has started. The research protocol remains DRAFT.** The budget is ₹0 and the delivery target is **4 December 2026**. Reviewer search runs alongside software work, screening, data-access checks and provisional extraction. A missing reviewer does not stop those activities; it prevents evidence from receiving independent-audit credit.

The application now has three commands: `check-workbook`, `screening-report` and `collect-sources`. The read-only workbook checker detects missing/duplicate IDs, broken links, invalid order pages, mismatched values, invalid review attribution, post-cutoff sources, unverified legal availability and selection inconsistencies. It adds the requested **duplicate Included-matter guard**, checks template formula fingerprints, and flags edited example rows or input beyond the formula ranges.

The checker reports **input validity**, outstanding obligations and preparation counts. It does **not** recalculate workbook formulas, certify reviewer identity or source contents, verify actual market coverage, reconstruct model snapshots, or issue a research PASS. Its research decision is always **NOT EVALUATED**. [Implemented scope](docs/technical-reference.md)

## Run the project

Use Python 3.11 or later from this project directory. The local implementation was checked with Python 3.12, openpyxl 3.1.5 and pypdf 6.21.4.

```powershell
python -m venv .venv-pilot
.\.venv-pilot\Scripts\python.exe -m pip install -r requirements-pilot.lock
.\.venv-pilot\Scripts\python.exe -m evidrava check-workbook --workbook references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx --out runs/my-first-check
.\.venv-pilot\Scripts\python.exe -m unittest discover -s tests -v
```

Open `runs/my-first-check/report.html`. The same directory contains `validation.json` and a checksum manifest. Choose a **new output directory for every run**; existing reports are never overwritten. On macOS or Linux, use `.venv-pilot/bin/python` instead of the Windows interpreter path. [Current preparation report](pilot/development/evidrava-workbook/report.html)

The earlier `python -m sebi_benchmark` command remains a compatibility alias. Use the `python -m evidrava` invocation shown above on this Windows machine: editable installation succeeded, but Windows Application Control blocked the generated console executables. Received workbook/proposal filenames and historical reports retain their original names for provenance.

Make a study copy for data entry; preserve the received original. Use rows 6 onward because row 5 contains fictional examples. Freeze, cutoff and reviewer fields must reflect real decisions and reviews.

```powershell
New-Item -ItemType Directory -Force working
if (Test-Path working/registry.xlsx) { throw 'Study copy already exists; choose a new filename.' }
Copy-Item references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx working/registry.xlsx
```

When `Snapshot!B3` is populated, pass `--sessions path/to/sessions.csv`. This file needs a `date` column with unique ISO dates from the applicable venue calendar. The daily pilot supports date-only publication and actual trading-session snapshot dates. Its one-calendar-day lag is not an intraday replay engine.

A frozen workbook also requires `--selection-manifest path/to/selection.json`, containing `{"selected_matter_ids": ["M001", "M002"]}` from the preserved draw. This prevents deleted registry rows from silently shrinking the sample. The checker does not establish the randomness or provenance of the draw.

## Start the screening exercise

The next measured task is the 30-record workload exercise. A working copy is at `working/screening_30.csv`; preserve the original in `pilot/screening/`. If setting up a fresh checkout, copy the original to that working location without overwriting existing entries. You can be the person doing this first screening; `human_reviewer_id` here identifies the screener and does not imply independent audit.

Keep the first 12 columns unchanged. Open each linked source, enter an `include`, `exclude` or `uncertain` decision with its reason, and record actual minutes for screening, grouping and predecessor search. Enter an explicit zero for a component only when no time was spent on it; leave unmeasured values blank. Record access waiting separately. [Fields and accepted values](docs/data-and-feasibility.md#recording-the-screening-exercise)

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava screening-report --csv working/screening_30.csv --out runs/screening-01
```

The command writes `screening.json`, `report.html` and a manifest. It verifies the original batch and all nine archived responses offline, then reports progress and timing by listing-date interval. Incomplete timings never become zero or enter the completed-time median. A fully recorded uncertain attempt remains an open follow-up. The [current report](pilot/development/evidrava-screening/report.html) has 30 pending records and no invented timing estimate.

Optional `--candidate-listings 100` gives an explicitly illustrative initial-screening workload only after all 30 records have valid, complete timing observations. It assumes the same listing mix and effort, excludes subsequent follow-up/annotation/audit, and is not a frame-wide estimate or deadline promise.

## Collect sources for review

The first three records now have [local source packets](pilot/sources/recon-first-three/report.html): three original PDFs with 5, 32 and 20 pages, their landing pages, page-labelled native text and a [provenance manifest](pilot/sources/recon-first-three/manifest.json). These are the first records of the fixed workload exercise, not a random sample or confirmed eligible matters.

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava collect-sources --ids RECON-01 RECON-02 RECON-03 --out runs/source-batch-01
```

This command makes bounded requests to official SEBI HTTPS addresses. It verifies the preserved reconnaissance batch, records retrieval timestamps and hashes, and preserves partial failures for inspection. Multiple PDF candidates remain ambiguous; the collector does not guess. No OCR, claim interpretation or human sign-off is performed.

Open the original PDF alongside the text. PDF page positions may differ from printed page labels, and extracted text may lose tables or layout. Retrieval timestamps and listing dates do not establish verified publication dates. The next practical task is to screen these three sources and enter your actual decisions and timings in the working CSV. Independent audit can follow when a reviewer is available.

## Next pilot work

1. Use the source packets and checker while seeking an independent human reviewer. Provisional extraction remains unaudited.
2. Time the [30-record screening exercise](pilot/screening/screening_30.csv), measure grouping/predecessor effort and choose a feasible frame scope. This is separate from the random research sample.
3. Check historical identity and free market-data coverage for conduct and feature warm-up. Earlier access probes alone do not establish coverage.
4. Freeze the reconciled frame, sampling rules and protocol before drawing about 40 matters. Process the first five and reforecast effort from observed researcher and reviewer time.
5. Evaluate statistical rules and Isolation Forest where the data support them. Defer H1 if suitable historical training labels are unavailable.

The 20-hour engineering increment remains a planning cap. Earlier work was not timed. New session records distinguish observed agent elapsed time from human active effort. No completed-audit or research-release claim is made while reviewer capacity remains unconfirmed. [Pilot Plan](docs/pilot-plan.md)

## Project documents

| Document | Read it for |
| --- | --- |
| [Pilot Plan](docs/pilot-plan.md) | Seven development steps, short iterations, parallel work and pending dependencies. |
| [Research Method](docs/research-method.md) | Sampling, evidence, historical availability and research decision rules. |
| [Data and Feasibility](docs/data-and-feasibility.md) | Dated access observations, screening procedure and workload evidence. |
| [Technical Reference](docs/technical-reference.md) | CLI contract, implemented checks, workbook layout, verification and deferred design. |

## Other checks and sharing

The earlier JSON-schema design remains reference material. Its 33 acceptance scenarios are not all implemented by this preparation checker.

All **125 local application tests pass**: 43 preparation checks, 31 screening tests and 51 source-acquisition tests. The latest [build and verification record](pilot/development/evidrava-increment-2026-11-13.json) separates those tests, real source retrieval and the supplied workbook scenario report. The supplied 114-scenario suite has not been rerun here, and Excel compatibility remains unverified.

```powershell
.\.venv-design\Scripts\python.exe scripts/check_design.py
python scripts/prepare_screening_batch.py --verify-existing
python scripts/package_share.py --out dist/Evidrava_share.zip
```

The design environment uses [requirements-design.lock](requirements-design.lock). The packager creates a local source ZIP with a manifest, including the three public-source packets. It excludes environments, caches, generated runs, working annotation copies and raw market data, and refuses an existing filename. GitHub publication requires an explicit instruction each time.
