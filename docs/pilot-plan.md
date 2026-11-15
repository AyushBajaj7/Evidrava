# Pilot Plan

Evidrava has a ₹0 pilot budget and a **4 December 2026** delivery target. On **13 November**, the user finalized the name and authorized implementation and preparation alongside reviewer search. The protocol remains **DRAFT**, the research draw is pending, and an independent reviewer is still unconfirmed. [Project introduction and commands](../README.md)

## Parallel work

| Proceed now | Dependency before completion |
| --- | --- |
| Software, synthetic checks, reports and documentation | Local test evidence and explicit implementation limits. |
| Time the 30-record exercise; assess scope and predecessors | Measured screening, grouping and uncertainty before frame freeze. |
| Check free data access, identities and conduct/warm-up coverage | Case-specific evidence before claiming usable coverage. |
| Provisional source extraction and annotation practice | A distinct human audits evidence before it receives audit credit. |
| Reviewer outreach and review-process planning | Reviewer identity, availability and adjudication arrangements before audited results. |

Reviewer search is a parallel workstream, not a prerequisite for coding or provisional annotation. Preserve extractor identity and dates; leave auditor fields blank until real review occurs. AI-assisted extraction does not create a second human reviewer. Pending audit must remain visible.

The 13 November scope checkpoint needs measured observations. Its date alone does not settle scope. The existing 30 records are a workload exercise, separate from the research draw. Freeze and draw follow a settled frame, eligibility, cutoffs and review procedure. [Screening guide](data-and-feasibility.md#screening-and-timing)

## Seven development steps with short iterations

| Step | Pilot work | Evidence and status |
| --- | --- | --- |
| 1. Planning and feasibility | Establish question, ₹0 scope, workload and data access. | Draft plan and probes exist; human timing and full coverage remain open. |
| 2. Requirements | Specify evidence obligations, timing and decision precedence. | [Research method](research-method.md), v2.4 proposal and acceptance catalogue. |
| 3. Design | Use the workbook for the first five matters and a limited read-only checker. | v3.3 layout and pinned template contract; general importer deferred. |
| 4. Implementation | Build checker, workload report, hash-checked source queue, source collection, provisional review brief, bounded frame preparation and a local web stack. | Seven runnable commands plus separate frontend, middleware and backend with temporary workbook checks in Evidrava 0.7.2. |
| 5. Testing | Exercise valid/invalid inputs, missing obligations and output preservation. | Current count is recorded in the live-screening-status increment; this is separate from the supplied 114-scenario formula suite. |
| 6. Local release | Package source, manifests and preparation evidence. | Local outputs; no automatic GitHub push or scientific release. |
| 7. Maintenance | Version corrections, add regressions and assess affected results. | Preserve received sources; record the impact of future protocol amendments. |

Use short iterations with one active engineering item and one annotation batch per person. Demonstrate a runnable result, inspect failures, record dependencies and select the next bounded increment. Keep scientific decisions separate from implementation choices.

## Current increment and next work

Evidrava 0.7.2 uses workbook v3.3, proposal v2.4 and the supplied tests as preserved references. The preparation checker, HTML/JSON reports, duplicate Included-matter guard and source/formula fingerprint checks are implemented. The checker never issues a research PASS and does not replace workbook recalculation or human audit. [Preparation report](../pilot/development/evidrava-workbook/report.html)

The implemented `screening-report` checks the working copy of the fixed 30-record CSV offline. It distinguishes completed screening attempts, complete timed observations and unresolved follow-ups. The [current report](../pilot/development/evidrava-screening/report.html) shows 0 of 30 completed. Input protection and timing summaries do not replace measured human screening. [Run the exercise](../README.md#start-the-screening-exercise)

The source-preparation increment has now preserved official material for all 30 fixed-workload records across three packets. Thirty records were acquired after a bounded retry; 29 have native text and RECON-08 remains explicitly encrypted. A legitimate SEBI order embedded beside unrelated external appeal links is now handled without following those external links, and its rejection is recorded. Eligibility, public dates, evidence interpretation and all human screening fields remain unverified. [Source-preparation record](../pilot/development/evidrava-source-preparation-2026-11-16.json) · [Packet index](../pilot/sources/recon-remaining-2026-11-16/report.html)

The screening-queue increment now checks the fixed source packets before linking every workload record to its preserved original PDF, page text and page inventory. Its generated navigation export is not a working annotation file: the person screening must still record actual decisions, locators, grouping/predecessor evidence and minutes in `working/screening_30.csv`. It makes the encrypted RECON-08 limitation visible and creates no screening decision or audit credit. [Current queue](../pilot/development/evidrava-screening-queue-v0.7.1-2026-11-16/report.html) · [Reviewer guide](reviewer-guide.md)

The 14 November increment adds a [provisional review brief](../pilot/screening/brief-first-three/report.html) from three machine-assisted records and 15 page anchors. One record is a compliance-only exclusion candidate; two need predecessor and data-coverage work. All remain **PENDING_HUMAN_REVIEW**. The command verifies file hashes, page references and anchor text mechanically; it does not establish the interpretation or complete human screening. [Latest verification record](../pilot/development/evidrava-increment-2026-11-15.json)

The 15 November source increment captured ten official SEBI predecessor records for the two uncertain matters. It located pre-2011 disclosures about HTL and DSQ activity, while preserving separate respondents, page dates, order dates and retrieval timestamps. The DSQ order references earlier 2002 and 2003 orders, and the Home Trade order references earlier website notices; these remain the next retrieval leads. Neither episode has a first-disclosure date, human decision or audit credit. [Predecessor review](../pilot/screening/predecessor-review-2026-11-15.html) · [Increment record](../pilot/development/evidrava-predecessors-2026-11-15.json)

The frame increment adds a structural candidate-frame check and a deterministic group-preserving sample draw. It is ready for future frozen inputs, but no candidate frame, protocol freeze or research draw has been created. The draw refuses any DRAFT protocol or frame whose bytes differ from the frozen hash; it cannot bypass the open timing, scope, eligibility or audit work. [Templates](../pilot/templates/) · [Technical contract](technical-reference.md#candidate-frame-and-sample-draw-commands)

The web-stack increment adds a local browser console with separate frontend, middleware and backend folders. It can display project state, temporarily check a selected workbook copy, and send pasted candidate-frame/protocol text through bounded APIs, but it never writes research files or changes `NOT_EVALUATED` to a research PASS. The services and their configured connections are enforced as loopback-only and are tested together with an ephemeral in-process stack. [Web-stack contract](technical-reference.md#local-frontend-middleware-and-backend)

Next, continue source-by-source review of the captured packets, retrieve the cited predecessors and record actual screening, grouping and predecessor-search minutes. Do not copy suggestions into human fields without performing that work. Continue through the 30-record exercise before choosing scope. Check linkage and warm-up coverage, preserve the sampling manifest, freeze before selection, and process the first five selected matters. Record extractor, reviewer, and adjudication time separately in [`pilot/screening/first_five_effort_log.csv`](../pilot/screening/first_five_effort_log.csv) (`matter_id,extractor_id,reviewer_id,extraction_minutes,review_minutes,adjudication_minutes,notes`). Provisional extraction can continue during reviewer search; independent audit and a completed research decision remain pending. Reforecast the remaining sample from measured first-five effort.

## Engineering cap and time records

| Work | Planned maximum |
| --- | ---: |
| Small workbook/contract adjustments | 4 hours |
| Read-only checker | 8 hours |
| Negative cases, agreement checks and rerun | 5 hours |
| Draft report and handoff | 3 hours |
| **Total planned increment** | **20 active engineering hours** |

Historical work on the supplied files was not measured, so compliance with the cap cannot be claimed. The earlier [application test record](../pilot/development/evidrava-increment-2026-11-15.json) reports 147 tests before the standalone predecessor helper was added, and the [source increment record](../pilot/development/evidrava-predecessors-2026-11-15.json) preserves its real acquisitions. The 0.4.0 [release verification record](../pilot/development/evidrava-release-2026-11-15.json) records 160 passing tests; the later [frame increment record](../pilot/development/evidrava-frame-increment-2026-11-15.json) records 168 after the frozen-only draw, the [web-stack increment record](../pilot/development/evidrava-web-stack-increment-2026-11-15.json) records 172 after frontend/middleware/backend integration, the completed [workbook-upload increment record](../pilot/development/evidrava-workbook-upload-increment-2026-11-15.json) records 177 after temporary workbook validation and loopback-only safeguards, the [source-queue increment record](../pilot/development/evidrava-source-queue-increment-2026-11-16.json) records 181 after read-only queue generation, and the [live-screening-status increment record](../pilot/development/evidrava-live-screening-status-increment-2026-11-16.json) records 184 passing tests across the full suite. [Earlier work](../pilot/development/session-2026-11-13.json) remains preserved. Agent elapsed time is not human active-time accounting. Record future work honestly and re-plan when measured effort exceeds the allocation.

## Completion boundaries

Patent exploration is a separate bounded experiment track, not a deliverable promise. Record actual technical failures, baseline results and contributor provenance; inspect prior art before investing in a proposed mechanism. The first generic anchoring methods are existing baselines, so no novelty claim follows from improving on literal text matching. Keep private experiments out of local distribution packages and hold publication/presentations until the user and the relevant IP adviser decide the next step. This does not relax the scientific review requirements or replace the feasibility pilot.

The provisional target remains at least 20 strict usable episodes across 10 independent related-matter groups from the agreed sample, plus the audit, leakage, coverage and reproducibility conditions. Thresholds are feasibility rules, not power calculations. A completed registry-only study can support CONDITIONAL when detector validation is unfinished; failed leakage or integrity checks remain NOT VALID.

Deliver the report by 4 December with its actual research and delivery status. Reviewer delay may leave evidence unaudited and delivery incomplete; it must not be hidden by altered sign-offs or reduced denominators. [Research decisions](research-method.md#pilot-decision)
