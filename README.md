# Evidrava

**A Point-in-Time Market Evidence Benchmark**

**Evidrava** is the finalized project name. The current local software version is **0.7.2**. This is an independent research project using public SEBI sources, with no claim of regulatory affiliation.

Evidrava builds a fair historical test for trading-anomaly detectors using public orders from the Securities and Exchange Board of India (SEBI). An order may describe conduct years after it happened. A model tested on 2019 data must not receive facts that first became public in 2024. Otherwise it has effectively seen the answers before the exam. This is **hindsight leakage**.

The registry records alleged or documented conduct, supporting passages and legal status. An order does not automatically establish wrongdoing by every named person or on every trading day. The project measures what public daily data and properly timed labels can support. [Research proposal v2.4](references/incoming/2026-11-13/Research_Proposal_v2.4_DRAFT_SEBI_Point_in_Time_Benchmark.docx)

## What we are building

| Part | Purpose | Available now |
| --- | --- | --- |
| Registry | Connect matters, instrument-specific episodes, order pages, public dates, label versions and human reviews. | [Workbook v3.3](references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx) |
| Preparation checker | Detect structural/evidence problems, count outstanding review obligations and write a local report. | [Python implementation](evidrava/) and [local tests](tests/test_checker.py) |
| Screening workload | Track the fixed 30-record exercise, complete timings, missing fields and unresolved follow-ups. | [Screening report](pilot/development/evidrava-screening/report.html) and [screening tests](tests/test_screening.py) |
| Source collection | Save official documents, byte hashes and provisional text labelled by PDF page. | [All 30 fixed-workload source packets](pilot/development/evidrava-source-preparation-2026-11-16.json) and [acquisition tests](tests/test_sources.py) |
| Human screening queue | Verify all prepared packets and point each workload record to its original PDF and navigation text without creating a decision. | [Current queue](pilot/development/evidrava-screening-queue-v0.7.1-2026-11-16/report.html) and [queue tests](tests/test_screening_queue.py) |
| Provisional review brief | Link machine-assisted observations and open questions to checked source pages. | [First three source notes](pilot/screening/brief-first-three/report.html) and [brief tests](tests/test_brief.py) |
| Predecessor source review | Preserve earlier official orders and compare episode scope, dates and legal-party scope. | [Ten-source review](pilot/screening/predecessor-review-2026-11-15.html), with [main captures](pilot/sources/predecessors-2026-11-15/report.html), [Home Trade supplement](pilot/sources/predecessors-supplement-2026-11-15/report.html) and [date supplement](pilot/sources/predecessors-date-supplement-2026-11-15/report.html) |
| Frame and sample preparation | Validate a declared candidate frame and, only after protocol freeze, make a deterministic group-preserving selection manifest. | [Templates](pilot/templates/) and [frame tests](tests/test_frame.py); no real frame or study draw has been made. |
| Local web console | Provide a browser UI through an explicit frontend → middleware → backend boundary. | [Frontend](frontend/), [middleware](middleware/), [backend](backend/) and [end-to-end tests](tests/test_web_stack.py). |
| Workbook regression suite | Populate synthetic cases and check formula results using LibreOffice. | [114 supplied scenarios](references/incoming/2026-11-13/registry_tests_v33/README.md); the author's run passed, local recalculation pending. |
| Research protocol | Define sampling, timing, audit, evaluation and the feasibility decision. | [Research Method](docs/research-method.md) and the draft proposal. |

A **matter** is an underlying proceeding that may have several orders. An **episode** identifies an instrument and conduct interval. Related matters share a group for independence counts and evaluation splits. Source publication, model availability and the date a person audited the evidence are separate facts.

## Current status

**Development has started. The research protocol remains DRAFT.** The budget is ₹0 and the delivery target is **4 December 2026**. Reviewer search runs alongside software work, screening, data-access checks and provisional extraction. A missing reviewer does not stop those activities; it prevents evidence from receiving independent-audit credit.

The application now has nine commands: `check-workbook`, `screening-report`, `screening-queue`, `collect-sources`, `review-brief`, `frame-check`, `draw-sample`, `simulate-seeds` and `check-market-data`. A separate local web stack adds a browser frontend, a strict middleware boundary and a backend API. The read-only workbook checker detects missing/duplicate IDs, broken links, invalid order pages, mismatched values, invalid review attribution, post-cutoff sources, unverified legal availability and selection inconsistencies. It adds the requested **duplicate Included-matter guard**, checks template formula fingerprints, and flags edited example rows or input beyond the formula ranges.

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

## Run the local web console

The browser console is split deliberately into three local services. The frontend has no direct project-file access; it calls only middleware, which exposes a small allowlisted API to the backend. The backend checks an uploaded workbook copy and pasted frame/protocol text only in temporary files, and never changes the workbook, screening CSV, source packets or `working/` folder.

| Service | Local address | Responsibility |
| --- | --- | --- |
| Frontend | `http://127.0.0.1:5173` | Browser UI and local manifest download. |
| Middleware | `http://127.0.0.1:8001` | Allowlisted routes, same-origin CORS, request-size limit and request IDs. |
| Backend | `http://127.0.0.1:8002` | Read-only status, temporary workbook checks, frame validation and frozen-only sample draw. |

```powershell
.\.venv-pilot\Scripts\python.exe scripts/run_web_stack.py
```

Open `http://127.0.0.1:5173` and stop all three services with `Ctrl+C`. The console can check a selected copy of the supported v3.3 workbook, validate pasted candidate-frame text and return a selection manifest from a genuinely frozen protocol. Its screening card reads only aggregate progress from `working/screening_30.csv`; it never exposes names, decisions, notes, timings or locators in the browser. Workbook, optional session-calendar and selection-manifest inputs are handled only for the request and are not stored in the project. The services and their connections are enforced as `127.0.0.1` only. Every result remains `NOT_EVALUATED` for research. It is local-only and is not a deployed website.

Make a study copy for data entry; preserve the received original. Use rows 6 onward because row 5 contains fictional examples. Freeze, cutoff and reviewer fields must reflect real decisions and reviews.

```powershell
New-Item -ItemType Directory -Force working
if (Test-Path working/registry.xlsx) { throw 'Study copy already exists; choose a new filename.' }
Copy-Item references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx working/registry.xlsx
```

When `Snapshot!B3` is populated, pass `--sessions path/to/sessions.csv`. This file needs a `date` column with unique ISO dates from the applicable venue calendar. The daily pilot supports date-only publication and actual trading-session snapshot dates. Its one-calendar-day lag is not an intraday replay engine.

A frozen workbook also requires `--selection-manifest path/to/selection.json`, containing `{"selected_matter_ids": ["M001", "M002"]}` from the preserved draw. This prevents deleted registry rows from silently shrinking the sample. The checker does not establish the randomness or provenance of the draw.

## Prepare the candidate frame before a draw

Use this only after the 30-record exercise and case review have produced a real, reconciled candidate frame. The supplied CSV template is intentionally empty; it does not represent a study sample. `frame-check` verifies the exact four-column frame, required reasons, unique matter IDs and whole related-matter groups, but it does not validate the human eligibility judgment.

```powershell
Copy-Item pilot/templates/candidate-frame-template.csv working/candidate-frame.csv
.\.venv-pilot\Scripts\python.exe -m evidrava frame-check --frame working/candidate-frame.csv --out runs/frame-check-01
```

Only after the protocol, target and seed have been genuinely settled should you copy `pilot/templates/frozen-protocol-template.json`, replace its frame hash with the `frame-check` result, and change its state to `FROZEN`. To prevent seed fishing, commit the frame hash to Git before determining the seed from an external verifiable source (e.g., closing index). Then the following creates an immutable, whole-group selection manifest that the frozen workbook can consume:

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava draw-sample --frame working/candidate-frame.csv --protocol working/frozen-protocol.json --out runs/sample-draw-01
```

The command refuses a DRAFT protocol, altered frame bytes and targets that would split a related-matter group. The selection uses deterministic subset-sum over SHA-256 ranked groups; it is reproducible cluster sampling rather than simple random sampling and may favor certain group-size combinations. It does not draw the real study sample until you provide those frozen inputs, and it never turns the research decision into PASS.

### Simulate seed sensitivity before freeze

Before freezing the protocol seed, run a simulation over multiple candidate seeds on the candidate frame to inspect cluster-size distributions and empirical group selection probabilities:

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava simulate-seeds --frame working/candidate-frame.csv --target 40 --seeds 100 --out runs/seed-sim-01
```

### Validate market price data

Validate daily cash-equity OHLCV market price series and session calendar coverage against the [market data contract](docs/market-data-contract.md):

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava check-market-data --data fixtures/market/sample_market_data.csv --out runs/market-check-01
```

## Start the screening exercise

The next measured task is the 30-record workload exercise. A working copy is at `working/screening_30.csv`; preserve the original in `pilot/screening/`. If setting up a fresh checkout, copy the original to that working location without overwriting existing entries. You can be the person doing this first screening; `human_reviewer_id` here identifies the screener and does not imply independent audit.

Keep the first 12 columns unchanged. Open each linked source, enter an `include`, `exclude` or `uncertain` decision with its reason, and record actual minutes for screening, grouping and predecessor search. Enter an explicit zero for a component only when no time was spent on it; leave unmeasured values blank. Record access waiting separately. [Fields and accepted values](docs/data-and-feasibility.md#recording-the-screening-exercise)

### Open the prepared source queue

All 30 workload records now have hash-checked source material. Build a fresh local navigation queue before starting a batch; it verifies the original CSV, every packet file and the one-record retry coverage before producing links. It does not change `working/screening_30.csv` or fill a human field.

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava screening-queue --out runs/screening-queue-01
```

Open `runs/screening-queue-01/report.html`. Use its original-PDF links and extracted text to navigate, but enter decisions and actual minutes only in `working/screening_30.csv`. RECON-08 is explicitly encrypted and needs a legitimate manual route before any decision. Keep the queue output and source packets on the same drive so its portable local links work.

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava screening-report --csv working/screening_30.csv --out runs/screening-01
```

The command writes `screening.json`, `report.html` and a manifest. It verifies the original batch and all nine archived responses offline, then reports progress and timing by listing-date interval. Incomplete timings never become zero or enter the completed-time median. A fully recorded uncertain attempt remains an open follow-up. The [current report](pilot/development/evidrava-screening/report.html) has 30 pending records and no invented timing estimate.

Optional `--candidate-listings 100` gives an explicitly illustrative initial-screening workload only after all 30 records have valid, complete timing observations. It assumes the same listing mix and effort, excludes subsequent follow-up/annotation/audit, and is not a frame-wide estimate or deadline promise.

## Collect sources for review

All 30 records in the fixed workload exercise now have preserved official-source material. The [first packet](pilot/sources/recon-first-three/report.html), [remaining-record packet](pilot/sources/recon-remaining-2026-11-16/report.html) and [retry packet](pilot/sources/recon-retry-2026-11-16/report.html) together contain 30 acquired records: 29 with native text and one encrypted PDF (RECON-08). The [source-preparation record](pilot/development/evidrava-source-preparation-2026-11-16.json) links the exact packet manifests and keeps the original partial collection visible. This is source preparation, not human screening, a random sample or confirmed eligibility.

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava collect-sources --ids RECON-01 RECON-02 RECON-03 --out runs/source-batch-01
```

This command makes bounded requests to official SEBI HTTPS addresses. It verifies the preserved reconnaissance batch, records retrieval timestamps and hashes, and preserves partial failures for inspection. Multiple official PDF candidates remain ambiguous; the collector does not guess. An unrelated external PDF link is never followed; when an official candidate also exists, its rejection is retained in the packet manifest. No OCR, claim interpretation or human sign-off is performed.

Open the original PDF alongside the text. PDF page positions may differ from printed page labels, and extracted text may lose tables or layout. Retrieval timestamps and listing dates do not establish verified publication dates. The next practical task is to work through the prepared 30-record queue and enter your actual decisions and timings in the working CSV. Independent audit can follow when a reviewer is available.

## Next pilot work

The [provisional screening brief](pilot/screening/brief-first-three/report.html) contains 15 page-linked observations across three sources, proposed dispositions and specific follow-up questions. Every record remains **PENDING HUMAN REVIEW**. These machine-assisted notes do not populate the workbook or human screening CSV.

```powershell
.\.venv-pilot\Scripts\python.exe -m evidrava review-brief --packet pilot/sources/recon-first-three --notes pilot/screening/provisional-first-three-2026-11-14.json --out runs/review-brief-01
```

The command checks the source-packet fingerprint, retained files, record coverage, page inventory and quoted anchors. It rejects missing or invented anchors and added human-review fields. A matching quote does not prove that a summary is correct or that a case is eligible. Inspect its context in the linked PDF. Keep the packet and output on the same drive so relative links remain portable.

The [predecessor review](pilot/screening/predecessor-review-2026-11-15.html) adds ten official SEBI source records for Home Trade and Khandwala / DSQ Biotech. The sources indicate substantial pre-2011 disclosure leads, which may put both cases outside the draft 2011–2025 first-disclosure frame. They do not establish the first episode-specific public date. The report lists the cited 2002/2003 CSFB orders and Home Trade notices still to retrieve. No human decisions or audit credit were entered.

1. Continue source-by-source screening and provisional extraction while searching for an independent human reviewer. Keep human decision, timing and audit fields blank until the work occurs.
2. Retrieve the original 2002/2003 CSFB orders and the cited Home Trade notices/order. Compare their exact passages and dates before assigning first disclosure.
3. Time the [30-record screening exercise](pilot/screening/screening_30.csv), measure grouping/predecessor effort and choose a feasible frame scope. This is separate from the random research sample.
4. Check historical identity and free market-data coverage for conduct and feature warm-up. Earlier access probes alone do not establish coverage.
5. Freeze the reconciled frame, sampling rules and protocol before drawing about 40 matters. Process the first five and reforecast effort from observed researcher and reviewer time.
6. Evaluate statistical rules and Isolation Forest where the data support them. Defer H1 if suitable historical training labels are unavailable.

The 20-hour engineering increment remains a planning cap. Earlier work was not timed. New session records distinguish observed agent elapsed time from human active effort. No completed-audit or research-release claim is made while reviewer capacity remains unconfirmed. [Pilot Plan](docs/pilot-plan.md)

## Project documents

| Document | Read it for |
| --- | --- |
| [Pilot Plan](docs/pilot-plan.md) | Seven development steps, short iterations, parallel work and pending dependencies. |
| [Research Method](docs/research-method.md) | Sampling, evidence, historical availability and research decision rules. |
| [Data and Feasibility](docs/data-and-feasibility.md) | Dated access observations, screening procedure and workload evidence. |
| [Reviewer Guide](docs/reviewer-guide.md) | How a future independent reviewer can check evidence without prematurely certifying it. |
| [Technical Reference](docs/technical-reference.md) | CLI contract, implemented checks, workbook layout, verification and deferred design. |

## Other checks and sharing

The earlier JSON-schema design remains reference material. Its 33 acceptance scenarios are not all implemented by this preparation checker.

The current local 0.7.2 verification is recorded in the [live-screening-status increment](pilot/development/evidrava-live-screening-status-increment-2026-11-16.json). The 181-test 0.7.1 source-queue and 177-test 0.7.0 workbook-upload records remain historical evidence. The design checker also validated three schemas, three examples and twelve shape mutations; it does not run application or supplied workbook scenarios. The supplied 114-scenario workbook suite has not been rerun here. Direct Excel COM automation confirmed that the base incoming workbook (`SEBI_Episode_Registry_v3_3.xlsx`) opens cleanly with zero repair prompts across all 15 sheets; however, synthetic scenario generation in openpyxl reached an Office prompt during temporary scenario evaluation, so automated test runner execution in Excel remains uncertified. No repair or base workbook modification was made.

```powershell
.\.venv-design\Scripts\python.exe scripts/check_design.py
python scripts/prepare_screening_batch.py --verify-existing
python scripts/package_share.py --out dist/Evidrava_0.7.2_2026-11-16_live-status.zip
```

The design environment uses [requirements-design.lock](requirements-design.lock). The packager creates a local-only source ZIP with a manifest, including the 30-record source packets, the predecessor packet and two supplements, provisional review records and the release verification record. It excludes environments, caches, generated runs, working annotation copies, private research experiments and raw market data, and refuses an existing filename. Publication and public presentations are on hold during the proposed IP assessment. GitHub publication requires an explicit instruction each time.
