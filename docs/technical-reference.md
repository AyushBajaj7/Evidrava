# Technical Reference

Evidrava 0.7.2 implements a **read-only preparation checker** for workbook v3.3, an offline screening-workload report, a hash-checked human screening queue, bounded official-source collection, a provisional review brief, candidate-frame validation, a frozen-protocol sample draw and a local web console with temporary workbook checking. The first five selected matters will use the workbook as the working record. The normalized registry, general importer, historical replay engine and detector commands later in this document remain deferred designs. [Pilot plan](pilot-plan.md) · [Research method](research-method.md)

Use Python 3.11 or later and the pinned [pilot dependencies](../requirements-pilot.lock): openpyxl 3.1.5, et_xmlfile 2.0.0 and pypdf 6.21.4. The package and primary command are `evidrava`; `python -m sebi_benchmark` and the installed `sebi-benchmark` command remain compatibility aliases. Historical artifacts retain their original names and hashes.

Use `python -m evidrava` locally. Editable installation succeeded, but Windows Application Control blocked the generated `evidrava.exe` and `sebi-benchmark.exe` launchers; module invocation works. No machine policy was changed.

## Implemented command

```text
python -m evidrava check-workbook --workbook <registry.xlsx> --out <new-directory>
```

Optional inputs are `--sessions <sessions.csv>` and `--selection-manifest <selection.json>`. A populated Snapshot date requires a supplied venue session calendar with a unique ISO `date` column. A frozen workbook requires a separately preserved `selected_matter_ids` list. Input hashes are retained in the report. These checks do not verify the provenance of a calendar or the randomness of a draw.

The command produces `validation.json`, standalone `report.html` and `manifest.json`. It first writes a sibling temporary directory, then publishes the completed directory. Existing output directories are refused. Interrupted directories remain identifiable as incomplete; there is no recursive deletion. The workbook is never saved or changed.

| Exit | Meaning |
| --- | --- |
| 0 | Preparation check completed with no input errors; warnings and unfinished review may remain. |
| 2 | Command syntax error. |
| 3 | Preparation check completed and found input errors; inspect the report. |
| 4 | Input/output, format or configuration prevented completion. |

**Exit 0 is not a research PASS.** Every report sets `research_decision=NOT_EVALUATED`, records the actual freeze state and lists pending work. Review completion and audited-slot shares are conditional on entered assertions. Human identity, passage meaning, legal interpretation, actual market coverage and final study acceptance are not certified.

## Screening workload command

```text
python -m evidrava screening-report --csv <working.csv> --out <new-directory>
```

The default reference is `pilot/screening/screening_30.csv`; `--reference` can locate the preserved copy beside its manifest and raw captures. The command pins the original CSV hash, checks the preparer and nine response hashes/request parameters, and never calls the older preparer's fetching or timestamp-backfill functions. It accepts exactly the original 27-column schema. The first 12 fields must match by ID; sorting is allowed, adding/removing/repeating records is not.

Outputs are `screening.json`, `report.html` and a checksum manifest, using the same no-overwrite output mechanism as workbook reports. Exit 0 includes ordinary IN_PROGRESS with blank human fields, exit 3 reports invalid entries, and exit 4 means analysis could not complete. The report remains separate from independent-audit certification and research acceptance.

Complete timing statistics use valid completed attempts with all three active-duration fields. Partial logged effort and waiting are separate; each statistic has its observation count. Empty timing cohorts remain null. Nonfinite entries, overflowing combined durations and overflowing workload projections are rejected. `--candidate-listings <N>` permits an explicitly conditional initial-screening scenario only after full timing coverage; it assumes the observed listing mix and excludes later follow-up, annotation, audit and linkage work. [Implementation](../evidrava/screening.py) · [Tests](../tests/test_screening.py) · [Entry guide](data-and-feasibility.md#recording-the-screening-exercise)

## Screening source queue command

```text
python -m evidrava screening-queue --out <new-directory>
```

By default, the command verifies the preserved 30-record reference and the three known workload source packets. It hashes every packet file, rejects a changed or duplicate acquired record, requires complete `RECON-01` through `RECON-30` coverage, and writes `screening-queue.json`, `screening-queue.csv`, `report.html` and an output manifest. The result uses only portable relative links, so the queue output and packets must share a filesystem volume. An explicit `--source-packet <directory>` can replace the defaults when reproducing a packet set.

The queue is a navigation artifact, not an annotation form. It contains the official listing URL, original PDF, extracted navigation text, extraction status and a generic human-work checklist; it never reads or changes the working CSV. The generated queue flags the encrypted RECON-08 source explicitly. Hash agreement proves retained source bytes, not eligibility, legal interpretation, public availability, reviewer independence or research readiness. [Implementation](../evidrava/screening_queue.py) · [Tests](../tests/test_screening_queue.py) · [Reviewer guide](reviewer-guide.md)

## Candidate-frame and sample-draw commands

```text
python -m evidrava frame-check --frame <candidate-frame.csv> --out <new-directory>
python -m evidrava draw-sample --frame <candidate-frame.csv> --protocol <frozen-protocol.json> --out <new-directory>
```

The candidate frame has exactly four UTF-8 CSV columns: `matter_id`, `related_matter_group`, `eligibility_status` and `eligibility_reason`. Status is `eligible`, `excluded` or `pending`; every row needs a stated reason, and every eligible matter needs a stable related-matter group. `frame-check` retains the exact frame SHA-256, preserves pending/excluded rows in its counts, and reports `READY_TO_FREEZE` only when its structural diagnostics are clear. It does not assess whether the stated eligibility reason is correct.

`draw-sample` requires a separate JSON protocol with explicit `state: FROZEN`, a timezone-aware `frozen_at`, an exact `frame_sha256`, seed, target count, algorithm `evidrava-group-draw-v1` and `replacement_policy: none`. It rejects DRAFT protocols, altered frame bytes and impossible exact targets. The deterministic draw selects whole related-matter groups only, writes `selection-manifest.json` with `selected_matter_ids` for the workbook checker, and never replaces records. Any later frame or protocol amendment needs a new frozen protocol and a new manifest. Both commands leave the research decision `NOT_EVALUATED`.

**Statistical draw mechanics and properties:**
- **Dynamic programming subset-sum:** `_select_groups` ranks candidate groups by `SHA-256("evidrava-group-draw-v1\0" + seed + "\0" + group_id)` and finds the first combination of whole groups that sums exactly to `target_matters` (e.g. 40).
- **Not simple random sampling (SRS):** This is deterministic cluster sampling under an exact knapsack constraint, not SRS. It avoids splitting connected matters across splits, but solving the exact subset-sum in rank order can favor specific group-size combinations (such as small 1-matter groups that fill the remaining capacity to reach the target).
- **No stratum column:** Although proposal v2.4 discussed stratification across periods and case types, the candidate frame schema (`matter_id`, `related_matter_group`, `eligibility_status`, `eligibility_reason`) does not contain a stratum column. Selection is purely cluster-based. Pre-freeze sensitivity analysis across multiple candidate seeds is strongly recommended.
- **Commit-before-seed protocol:** To eliminate seed-fishing concerns, the candidate frame CSV and frozen protocol draft must be committed to the public Git repository before fixing the seed from an external, publicly verifiable source (e.g. market index close or public randomness beacon). [Templates](../pilot/templates/) · [Implementation](../evidrava/frame.py) · [Tests](../tests/test_frame.py)

## Local frontend, middleware and backend

The local console is deliberately split across [`frontend/`](../frontend/), [`middleware/`](../middleware/) and [`backend/`](../backend/). Run all three with `python scripts/run_web_stack.py`, then open `http://127.0.0.1:5173`. The default ports are frontend `5173`, middleware `8001` and backend `8002`, all bound to loopback.

The frontend serves static HTML, CSS and JavaScript and obtains its API address from local `config.js`. It displays safe status, can check a selected workbook copy, sends pasted frame/protocol text, and can download a returned selection manifest. The screening status is recalculated from the local working CSV as aggregate counts only; names, decisions, notes, timings and locators never leave that file through the API. An unavailable or structurally invalid working file is shown as an input-state warning, with diagnostics remaining in the offline CLI report. The middleware allows only `GET /health`, `GET /api/v1/project-status`, `GET /api/v1/templates`, `POST /api/v1/workbook/check`, `POST /api/v1/frame/check` and `POST /api/v1/sample/draw`; it rejects unapproved origins, routes, methods and oversized requests before forwarding. All three services bind and connect only to `127.0.0.1`. The workbook route alone has a bounded 32 MB encoded-request limit so that a decoded 20 MB workbook and optional local inputs can fit; other requests use the smaller limit. The backend never accepts browser file paths, uses temporary files for workbook/frame/protocol processing, and never writes the workbook, screening CSV, source packets, `working/` or `runs/` directories. Optional session-calendar and selection-manifest text is validated only for that request. Each API response remains `NOT_EVALUATED` for research. [End-to-end tests](../tests/test_web_stack.py) · [Aggregate-status tests](../tests/test_backend_status.py)

The current local verification is recorded in the live-screening-status increment. It includes source-queue, aggregate dashboard-status and web-stack tests. A direct loopback launch previously validated the pinned workbook copy through all three services; the upload reported `VALID`, `temporary_upload_only=true`, `protocol=DRAFT` and `research_decision=NOT_EVALUATED`. This is software verification only, not workbook-formula recalculation in Excel or a research result.

## Source collection command

```text
python -m evidrava collect-sources --ids RECON-01 RECON-02 RECON-03 --out <new-directory>
```

Choose explicit, distinct IDs from the preserved 30-record reconnaissance batch. The default `--reference` is the same original CSV used by `screening-report`; its fingerprint, preparer and nine raw captures are verified before collection. The command does not read or fill human entries in the working CSV.

Only HTTPS URLs on `www.sebi.gov.in` or `sebi.gov.in` are accepted, including redirects and discovered document links. The collector recognizes direct PDFs, ordinary PDF links and the archive's `file=` viewer links. It deduplicates candidates and leaves multiple official candidates AMBIGUOUS rather than choosing one. An unrelated external PDF link is never followed; if an official candidate is also present, the rejected link is recorded in the packet manifest. A missing PDF, invalid PDF signature, failed request or failed extraction receives an explicit status. Successfully retrieved bytes remain available when later extraction fails.

Each invocation is limited to 30 named records, 2 MB per HTML response and 20 MB per PDF response. Streamed bytes are checked against the limit and declared length. Requests use a 20-second I/O timeout, at most four redirects, no automatic retries and a one-second pause between fetches. The I/O timeout is not a total wall-clock deadline. Native text extraction uses pypdf 6.21.4 with page/content/text limits; it performs no OCR or legal interpretation. Encrypted and textless files retain their extraction status and require separate handling.

Redirect bodies are closed unread before following a validated destination. Interrupted HTTP bodies are recorded as per-record failures so later records can still be collected. PDF content limits are checked after decompression; extraction is not isolated behind a hard memory or execution-time limit. The initial packet's `timeout_seconds_per_request` field describes the same I/O timeout; current manifests name it `socket_timeout_seconds`.

Each record receives the original response files plus `pages.json` and `text.txt` when extraction completes. The top-level `manifest.json` records URLs, retrieval timestamps, hashes, byte counts, extraction status, reference provenance and software fingerprints; `report.html` links the review files. The output directory must be new. Work is written in a sibling incomplete directory and renamed on completion; previous outputs are preserved. Exit 0 means all requested sources were acquired, exit 3 means partial or failed acquisition, and exit 4 means setup or output could not complete. An acquired file may still be encrypted or have no native text; inspect its extraction status.

All packets state `human_screening_completed=false`, `publication_dates_verified=false` and `research_decision=NOT_EVALUATED`. The completed [30-record source-preparation inventory](../pilot/development/evidrava-source-preparation-2026-11-16.json) remains source preparation, not independent audit. [Implementation](../evidrava/sources.py) · [Tests](../tests/test_sources.py) · [Packet manifest](../pilot/sources/recon-remaining-2026-11-16/manifest.json)

## Provisional review brief command

```text
python -m evidrava review-brief --packet pilot/sources/recon-first-three --notes pilot/screening/provisional-first-three-2026-11-14.json --out <new-directory>
```

The notes identify their preparation date, AI-assisted author, draft scope and source-packet manifest hash. Each record has a screening ID, suggested disposition, rationale, observations and open questions. Each observation supplies a PDF page, a paragraph label, a short text anchor and a provisional summary. The [first notes file](../pilot/screening/provisional-first-three-2026-11-14.json) contains three records and 15 anchors; it is separate from the human screening CSV.

The command verifies input fingerprints, source relationships, page references and anchor text after whitespace normalization. A matching anchor proves only that the quoted text appears on the recorded extracted page. It does **not** establish that the surrounding summary follows from it, validate a paragraph label, determine legal meaning, verify public availability or confirm eligibility. The report keeps these limits visible and leaves every record **PENDING_HUMAN_REVIEW**.

Outputs are `brief.json`, `report.html` and `manifest.json` in a new directory. The brief provides source links and open questions without changing downloaded packets, the received workbook/proposal or human screening entries. No human timing, reviewer identity, sign-off or research PASS is generated. Inspect the original PDFs and source context before making any human entry. [First brief](../pilot/screening/brief-first-three/report.html) · [Implementation](../evidrava/brief.py) · [Tests](../tests/test_brief.py)

## Bounded predecessor capture

This one-off helper captures an explicit list of official SEBI predecessor leads. It is not one of the four `evidrava` application commands and does not crawl search results or infer matter relationships.

```text
python scripts/capture_predecessors.py --plan pilot/screening/predecessor-plan-2026-11-15.json --out runs/predecessors-01
```

To regenerate only a safe derived index after verifying every retained packet file, use:

```text
python scripts/capture_predecessors.py --refresh-report pilot/sources/predecessors-2026-11-15
```

Plans contain one to twelve distinct `PRE-01` through `PRE-12` IDs, a source URL, one or more original `RECON-01` through `RECON-30` workload IDs, a source title and a relationship note. The helper preflights every URL and accepts only HTTPS on the SEBI host allowlist. Each explicit response is limited to 2 MB for HTML and 20 MB for PDFs, with a 20-second I/O timeout, no retries, at most four validated redirects and a one-second pause between requests. A new output directory is required.

HTML is retained byte for byte with decoded native text. PDFs are retained byte for byte with `pages.json` and page-labelled `text.txt` when extraction is possible. There is no OCR or claim interpretation. The manifest records source and output hashes, URLs, HTTP status, capture timestamps and extraction status; `report.html` links originals and extracted text. All outputs mark human review and publication-date verification false and the research decision `NOT_EVALUATED`.

An HTTP 200 response and a readable date printed on a page do not prove when that source first became public. Keep page date, order/signature date and capture time separate. For HTML, extracted text has no stable PDF page locator. A reviewer must inspect the original page and decide whether a passage discloses the specific episode. The [15 November review](../pilot/screening/predecessor-review-2026-11-15.html) covers ten captured sources across [the main packet](../pilot/sources/predecessors-2026-11-15/manifest.json), [Home Trade supplement](../pilot/sources/predecessors-supplement-2026-11-15/manifest.json) and [date supplement](../pilot/sources/predecessors-date-supplement-2026-11-15/manifest.json). [Implementation](../scripts/capture_predecessors.py)

## Implemented checks and boundaries

Brief output and source packets must be on the same drive. Relative links keep the project portable; cross-drive output is rejected clearly. The real-packet integration test copies the packet into its temporary workspace so Windows can run it when the repository and system temporary directory are on different drives.

- Pin the v3.3 schema, exact header positions, reserved example inputs and formula fingerprints to the accepted received workbook. Changed or missing formulas are errors; cached formula outputs are never used as proof of correctness. Fingerprint agreement does not recalculate a formula.
- Read literal study inputs from row 6 onward. Reject formulas in input cells, partially populated rows with missing IDs, whitespace identifiers, duplicate IDs and overflow beyond the fixed template bounds.
- Check matter/episode/version relationships, known whole-number order pages, citation bounds, typed public dates and collection cutoff. This release-scoped workbook treats post-cutoff orders as errors, matching v3.3. A separate full-history importer is deferred.
- Check registered distinct reviewers, the independence flag, dated audits, locators and values against their referenced registry fields. Missing or unaudited obligations retain their slots; a confirmed-unresolved disposition completes review without earning audit credit.
- Generate all-version required slots before joining evidence: two matter slots, two episode identity slots and three slots for each included version. An episode without a version still contributes three placeholder obligations. Multiple citations cannot inflate a slot's credit.
- Check legal-event status, scope, source and date ordering. Assumed-source events are reported as unverified and excluded from the documented-event count. The checker reports those events but does not implement snapshot replay.
- Compute descriptive delay counts/median only for verified disclosure passages. Report episodes with missing or assumed disclosure separately. Full denominator and inventory completeness remain provisional when records have errors or inventories are unfinished.
- Reconcile Included records and in-scope matters, document exclusions and reject duplicate Included rows. The extra duplicate guard is in Python; the received workbook is preserved byte for byte. A frozen sample manifest catches selected matters deleted from both the workbook and its log.
- Require the accepted All versions, independent-auditor and one-calendar-day settings. Populated Snapshot dates must be actual sessions in the supplied calendar; intraday dates are unsupported in this bounded pilot.

The checker does **not** recompute strict usable episode counts, independent qualifying groups, final PASS/CONDITIONAL/FAIL, market features, predictions or leakage outcomes. A manually recorded failed leakage test is an error; a passing flag is not proof that a model was tested. The report does not claim native workbook-suite execution. [Implementation](../evidrava/checks.py) · [CLI](../evidrava/__main__.py) · [Local tests](../tests/test_checker.py)

## Workbook layout

Headers are on row 4, fictional examples on row 5 and study records from row 6. The pinned [contract](../evidrava/workbook_contract.json) is generated from the exact received source; change it only after explicitly reviewing a new workbook version. It includes input columns, bounds, example values and per-sheet formula digests.

| Sheet | Input columns | Calculated columns | Last study row |
| --- | --- | --- | ---: |
| People | A:D | E | 45 |
| Matters | A:K | L:Z | 105 |
| Orders | A:K | L:M | 155 |
| Episodes | A:P | Q:AO | 155 |
| Versions | A:G | H:W | 255 |
| LegalStatus | A:J | K:L | 255 |
| Evidence | A:O and AB | P:AA | 805 |
| SelectionLog | A:I | J | 305 |

Evidence AB is the explicitly reviewed episode-disclosure flag. Matters Z checks for an Included selection row. The checker validates Rules inputs and reads only the manual leakage/baseline flags from Gates; it does not trust calculated dashboard values. [Workbook v3.3](../references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx) · [Supplied layout map](../references/incoming/2026-11-13/registry_tests_v33/maps.json)

## Source provenance and verification

The 13 November archive is preserved as exact extracted source files with a [receipt and hashes](../references/incoming/2026-11-13/receipt.json). No supplied fixture, expected output, workbook or proposal was edited. The requested additional duplicate-selection validation lives in the checker. Use a separate study copy for annotation.

| Current artifact | SHA-256 |
| --- | --- |
| `files (3).zip` | `9d67a942c5c54771c8eff9185983c3172bd056796a5d840af660532373749d8e` |
| `SEBI_Episode_Registry_v3_3.xlsx` | `b4e7a944eda1fba7509c61122cb670d8e1173070f2f5eef01f0d30df0789cd96` |
| `Research_Proposal_v2.4_DRAFT_SEBI_Point_in_Time_Benchmark.docx` | `69e13c9d97602f0a2675e50fbcff0c4a1654ba447f92ffc29fce090f26a1c972` |
| `SEBI_Registry_v3_3_tests.zip` | `65b09ab0a63fc000aa285961483c91a2a09c19f38d8d67462eff94c6e6d8c7d5` |

The supplied author-run LibreOffice report records **114/114 scenarios** and the mutation notes report **11/11 new mutations caught**. Earlier mutation experiments were not repeated. Formula/header inspection and supplied reports are distinct from local recalculation. LibreOffice is not installed here. A local Excel smoke attempt reached an Office repair prompt before one temporary scenario could finish; the prompt was not accepted, Excel was closed, and no supplied workbook or test input was changed. Excel compatibility therefore remains unverified. The upstream runner deletes its work directory and uses the default LibreOffice profile; any future rerun needs a verified disposable directory and isolated profile. [Supplied report](../references/incoming/2026-11-13/registry_tests_v33/last_run_report.txt) · [Mutation notes](../references/incoming/2026-11-13/registry_tests_v33/mutation_check.md)

The implementation's application tests exercise preparation semantics, the exact received template, formula/header/example tampering in memory, workload arithmetic, source acquisition, source-queue coverage, provisional brief checks, output hashes, overwrite refusal, the standalone predecessor-capture helper, candidate-frame drawing and the full local web stack including temporary workbook uploads. The current 0.7.1 verification is recorded in the [source-queue increment record](../pilot/development/evidrava-source-queue-increment-2026-11-16.json), with the earlier [workbook-upload increment record](../pilot/development/evidrava-workbook-upload-increment-2026-11-15.json), [web-stack increment record](../pilot/development/evidrava-web-stack-increment-2026-11-15.json), [frame increment record](../pilot/development/evidrava-frame-increment-2026-11-15.json), [release verification record](../pilot/development/evidrava-release-2026-11-15.json), [application test record](../pilot/development/evidrava-increment-2026-11-15.json) and [predecessor increment record](../pilot/development/evidrava-predecessors-2026-11-15.json) retained for history. It does not execute the supplied 114 workbook scenarios, and it does not establish Excel compatibility. [Installation and commands](../README.md#run-the-project)

The older received v3/v2.1 source and its 47-scenario supplied suite remain preserved for provenance, not current use. Their recorded hashes are retained below. [Older inputs](../references/incoming/2026-11-05/)

| Historical artifact | SHA-256 |
| --- | --- |
| `files.zip` | `5b2b26fd09ac423e0829d5b0dd3ba386462575ca85b69ca98402ff3ab80ffe6d` |
| `SEBI_Episode_Registry_v3.xlsx` | `fccf00f8cac72741d8baec9f8838fadcb07798916a651d27048291a9900ae0d2` |
| `SEBI_Registry_v3_tests.zip` | `8ad8072f8521286fdcad08fc875832a6cd81b7b7552c8dfea9e70c0da3c3dd47` |
| `Research_Proposal_v2.1_DRAFT_SEBI_Point_in_Time_Benchmark.docx` | `1927d0c75921409ff5b80d2dd0de7f9ceca710c728eccffd726ad2a4a280a826` |

The reference JSON design uses three schemas, three synthetic examples and 12 shape mutations. Four mutations are rejected by schema; eight deliberately preserve shape for later semantic tests. The 33 broad application scenarios remain DESIGNED_NOT_RUN; the new bounded preparation tests do not certify the full catalogue. [Acceptance catalogue](requirements/ACCEPTANCE_SCENARIOS.json) · [Design check](../scripts/check_design.py) · [Pinned design environment](../requirements-design.lock)

The remaining sections describe the **deferred full benchmark design**, not implemented commands or promises about this increment.

## Registry and time contracts

The reference design uses immutable JSON releases. Typed records capture matters, orders, episodes, label versions, claims, sources, evidence, reviews, scoped legal events and selection decisions. Selection records reference a separate checksummed frame. Orders belong to matters. Episodes have stable IDs and unique `(episode_id, version_no)` versions. Claims bind a typed value to a subject, field and revision. Reviews bind the audited value and version to distinct human identities, dates and outcomes. Evidence records point to exact source bytes and locators. [Registry schema](../schemas/registry.schema.json) · [Run schema](../schemas/run.schema.json) · [Report schema](../schemas/report.schema.json)

- Build expected slots from the frozen cohort and version inventory before joining evidence. Draft obligations are conduct start, conduct end and scheme per included label version, instrument and ISIN per episode, and legal status and order date per matter. The first two conduct fields and both identity fields are critical. An episode without a label version contributes three unresolved placeholder slots. `selected_claim_ids` chooses one immutable revision per subject and field. Earlier included label versions contribute slots, while superseded extraction revisions remain in history.
- Quarantine every row in an ID collision and its affected references. Check parent and target scope. Generate separate diagnostics for authoring issues, structural failures, evidence quality and readiness. An incomplete inventory has `denominator_complete=false`. Report null shares when the denominator is zero. Review completion counts finalized unresolved dispositions and qualifying audit counts only verified slots. A predeclared applicability rule and reviewed disposition govern N/A.
- For PDF evidence, require a matter-owned order, a known positive integer page count and a page in range. Official table locators identify the source hash and exact row key and column. The selected matter-level `order_date` refers to a specific order. Historical legal state comes from applicable reviewed events, with unresolved conflicts exposed when the policy gives no resolution.
- Retain event, public, retrieval, audit and release times independently. For each critical claim, take its earliest verified qualifying support. The latest of those critical times determines label readiness. First disclosure has separate evidence and each emitted value has its own availability. Assumed dates stay outside strict replay.
- Collection cutoff `C` governs release scope. A date cutoff includes the calendar day in the configured Asia/Kolkata timezone. An exact cutoff includes its boundary. For date-only evidence against an intraday `C`, collection eligibility stays unknown unless the full possible public-day interval fits. Model availability for date-only sources begins next trading session. Training information must be available by fit cutoff `c`, features by score time `t`, with `c ≤ t`. Same-session end-of-day bars enter only after their release.
- Use the highest eligible label-version number after checking lineage and public order. Later-public facts leave earlier views unchanged. Corrected extraction errors create a new release with an impact log. Retain source-vintage limitations for reconstructed historical inputs.
- Hash exact source bytes. Canonical JSON uses UTF-8, sorted keys, compact separators, `ensure_ascii=False` and `allow_nan=False`. Sort set-like lists by a declared stable key and preserve meaningful sequence order. A review value digest hashes canonical `{"claim_id": ..., "value": ...}`. Record release lineage, input/code/environment/schema/protocol/frame/calendar hashes and amendments.

Later analytical tables need historical identifier intervals and known-at times, venue calendars with session offsets, versioned market bars and corporate actions, coverage by required session, and features and predictions with fit/score times and model/input hashes. The evaluation manifest fixes the universe, folds, purge rules, matching/cooldown and scoring-label version. JSON files suit the small registry. Consider Parquet for larger panels and DuckDB when query measurements justify it.

## Requirements and acceptance scenarios

The catalogue covers the full reference benchmark. The pilot plan selects the bounded checker and workbook work. FR18 is conditional on suitable historical labels. [Acceptance catalogue](requirements/ACCEPTANCE_SCENARIOS.json)

| ID | Required behavior | Scenarios |
| --- | --- | --- |
| FR01 | Parse typed inputs, validate IDs and examples, record source and importer provenance. | AC01, AC25 |
| FR02 | Enforce unique IDs and references, quarantine collisions and map independent groups. | AC02, AC03, AC04, AC13 |
| FR03 | Preserve source bytes and locators, verify PDF page bounds. | AC05, AC06 |
| FR04 | Generate obligations from the frozen cohort and reviewed inventory, including missing rows. | AC07, AC08, AC09 |
| FR05 | Audit the matching claim version with distinct stable human IDs, dates and outcomes. | AC10, AC11 |
| FR06 | Report valid audit, review completion and strict-subset completeness separately. | AC07, AC08, AC09 |
| FR07 | Preserve version history, public-time evidence and authoring provenance. | AC14, AC15, AC18, AC19 |
| FR08 | Separate first disclosure, label readiness and individual field availability. | AC16, AC18 |
| FR09 | Validate legal-event status, source, times, scope and review. Preserve unknown history. | AC20, AC21 |
| FR10 | Verify historical identity, conduct and warm-up coverage, market actions and missing-session reasons. | AC22, AC23 |
| FR11 | Freeze protocol and frame before selection, retain ranking, exclusions and amendments. | AC12, AC24 |
| FR12 | Reconstruct scoped snapshots from collection, fit and score cutoffs. | AC15, AC17, AC18, AC26 |
| FR13 | Keep related matters together, enforce `c ≤ t`, fit transforms and thresholds with eligible data. | AC23, AC27 |
| FR14 | Recompute strict counts and decision precedence from inputs and group mappings. | AC09, AC12, AC13, AC28 |
| FR15 | Report diagnostics by entity, field, version and scope. | AC03, AC07, AC20, AC26 |
| FR16 | Reproduce statistical scores and Isolation Forest with recorded settings and seeds. Report infeasible folds. | AC29, AC30 |
| FR17 | Report known episode, matter and group recall, alerts per 1,000 scored instrument-sessions, clusters and timing. | AC30 |
| FR18 | Test strict versus hindsight training labels with fixed features, splits, scoring population and scoring labels, or defer H1. | AC31 |
| FR19 | Report sample usability, strata, exclusions and evidence coverage. Use design-aware frame estimates when supported. | AC32 |
| FR20 | Record reproducibility hashes, configuration, calendar, seeds, commands and numerical tolerances. | AC25, AC29 |
| FR21 | Produce a local deadline report with separate delivery and research states. | AC28, AC33 |
| FR22 | Preserve corrections, affected releases and result impacts. | AC18, AC19 |

| ID | Quality requirement | Verification |
| --- | --- | --- |
| NFR01 | Deterministic IDs, splits and counts, documented numerical tolerance. | AC25, AC29 |
| NFR02 | Trace accepted values and metric cohorts to evidence and a manifest. | AC06, AC11, AC25 |
| NFR03 | Distinguish missing, invalid and unknown states from real zero counts. | AC03, AC05, AC26, AC30 |
| NFR04 | Recreate the pinned local environment, measure runtime and memory before setting targets. | AC29, AC33 |
| NFR05 | Preserve source bytes and previous releases, version exports and record permissions. | AC19, AC25 |
| NFR06 | Use local zero-budget tooling. GitHub pushes require explicit user instruction. | Release review |

## Planned command interface

These commands are deferred reference interfaces. The runnable preparation, screening and source-collection commands are documented above and in the root README.

```text
python -m evidrava validate --bundle <registry.json> --config <run.json> --out <new-directory>
python -m evidrava report --run <completed-run-directory>
```

`validate` would read immutable inputs offline and write `manifest.json`, `diagnostics.json`, `expected_slots.json`, `validation.json` and `report.md`. `report` would verify the completed run and render a new report with renderer provenance. Finalize the local output directory through a sibling temporary directory and atomic rename. Reject an existing output path and retain interrupted work as incomplete. Print run ID, output path, research decision, delivery status and diagnostic counts. Sort diagnostics by scope, category, entity, path and code.

| Exit code | Planned meaning |
| --- | --- |
| 0 | Completed check with a reported research state, including DRAFT, CONDITIONAL or FAIL. |
| 2 | Invalid command syntax or unsupported option. |
| 3 | Invalid schema or configuration, unknown scope, structural failure or failed leakage check. |
| 4 | Operational failure such as unreadable input or interrupted write. |

Later command families cover workbook import, historical snapshots, coverage and features, evaluation, and local release. A release would contain the relevant permission record, reproducibility manifest and scientific limitations.
