# Research Method

Evidrava studies how delayed enforcement information and the limits of daily market data affect evaluation of trading anomaly detectors. Each record carries the allegation, supporting evidence and applicable legal status. The pilot evaluates feasibility and reports the limits of claims supported by the observed cases.

The working sources are [workbook v3.3](../references/incoming/2026-11-13/SEBI_Episode_Registry_v3_3.xlsx) and [proposal v2.4](../references/incoming/2026-11-13/Research_Proposal_v2.4_DRAFT_SEBI_Point_in_Time_Benchmark.docx). The 13 November execution instruction permits implementation, screening and provisional extraction alongside reviewer search. It does not waive independent audit, freeze the protocol or authorize an unrecorded research draw.

## Sample and registry

A **matter** is one underlying enforcement case that may have multiple orders. An **episode** covers an instrument and conduct interval within a matter. A **related-matter group** keeps connected proceedings together for independence counts and evaluation splits.

The draft scope covers cash-equity matters first publicly disclosed in 2011–2025 and proposes about 40 distinct matters. Confirm the population after assessing workload and access. Preserve listing dates and identifiers, follow predecessor orders, resolve related proceedings, and record eligibility and exclusion reasons. Freeze and checksum the eligible frame, canonical matter keys, sampling rules, ranking method, seed and quotas before drawing matters. Preserve the draw and any permitted replacement or amendment in the selection log. Linkage and evidence gaps in otherwise eligible sampled matters remain in the feasibility record. [Frame evidence and screening exercise](data-and-feasibility.md)

## Evidence and audit

Build expected slots from the sampled cohort, the episode inventory and all label versions included in the frozen release. The required fields are provisional until protocol freeze.

| Level | Required slots | Critical slots |
| --- | --- | --- |
| Included label version | Conduct start, conduct end, scheme | Conduct start and end |
| Episode | Instrument, ISIN | Instrument and ISIN |
| Matter | Legal status, order date | — |

An episode awaiting a label version carries a placeholder with the three version-level obligations. Reconcile the inventory against the frozen manifest so a deleted row cannot reduce the denominator. Superseded extraction revisions stay in history as revisions of a claim. The matter-level order-date slot requires a designated supporting order. A reviewed legal-status slot and a historical legal snapshot serve separate purposes.

Each accepted value needs a verified source locator, consistent links and an audit by a human distinct from the extractor. Record both IDs, dates, outcomes and any adjudication. Multiple citations can support a single slot. Count each slot once.

Work may begin before a reviewer is available. Record provisional extraction as such and leave its independent-review fields unset. The preparation checker reports missing audit obligations; it does not confer audit credit or establish that the registered reviewer is a real independent person.

Automated source collection preserves the downloaded document and its provenance, with native text indexed by PDF page position. A successful download or text extraction does not establish eligibility, passage meaning, first disclosure or legal status. Retrieval time and listing dates do not verify source-publication time. Inspect the original PDF before recording a source locator; printed page labels may differ from PDF positions. The first three [source packets](../pilot/sources/recon-first-three/report.html) belong to the workload exercise, not the random research sample.

| Evidence state | Counts toward review completion | Counts as verified evidence |
| --- | --- | --- |
| Missing, pending or extracted without independent review | No | No |
| Reviewed and finalized as unresolved or invalid | Yes | No |
| Independently audited and valid | Yes | Yes, subject to scope and public availability |
| Not applicable under a declared rule | Report separately after review | Excluded from applicable slots |

Divide valid audited slots and completed applicable review dispositions separately by expected applicable slots. A zero denominator produces an unavailable share. Missing evidence and unresolved links remain obligations. Each applicable critical slot remains required. An unfinished inventory makes known counts provisional and blocks a completed research decision. Report completeness within the strict subset as well as across the full sample.

## What the model can know

Keep conduct time, source public time and later extraction or audit time separate. The **collection cutoff `C`** bounds the release. The **fit cutoff `c`** bounds training and threshold selection. The **score time `t`** bounds prediction inputs. Require `c ≤ t`, and use the venue's trading calendar for session boundaries.

The confirmed rules count every included label version and make date-only sources model-visible from the next trading session. The v3.3 daily pilot implements a one-calendar-day lag and restricts queries to actual trading-session dates. The checker requires a supplied session-date calendar whenever the Snapshot date is populated. This restricted convention gives the intended date-only inclusion; it does not support intraday queries. Exact-timestamp-inclusive handling remains part of the deferred full engine. A date collection cutoff covers the whole local day. Preserve date precision and verification basis; a daily bar is usable only after its actual release.

First disclosure requires evidence that discloses the episode. Label readiness is the latest of the earliest verified support times across all critical fields. Each displayed field still needs its own public support. A later-public scheme classification or legal update enters only eligible snapshots and only for its target. Preserve applicable whole-matter and episode events. Leave an interpretation unresolved when the legal policy or evidence cannot resolve a conflict.

A legal event supported only by an assumed source-publication date is retained as **SOURCE DATE UNVERIFIED**, excluded from historical snapshots and documented-event counts, and counted separately on Gates. This uncertainty does not independently invalidate the decision. Required evidence slots still need valid support, and unresolved obligations remain in their denominator. Delay summaries use only verified first-disclosure dates and report episodes excluded for assumed or missing disclosure; candidate dates remain in the registry.

Selection reconciliation rejects an Included row whose matter is absent, an identified log row without a decision, and an in-scope matter without an Included log row. Documented exclusions are handled explicitly. The preparation checker also rejects duplicate Included rows for the same matter and checks a separately preserved selected-ID manifest for frozen workbooks. DRAFT retains precedence before freeze while integrity diagnostics remain visible.

Within a release, later-public facts leave earlier snapshots unchanged. When the team corrects an extraction of a fact that was already public, create a new release, document the correction and assess the effect on earlier reconstructed results. Preserve original releases and source fingerprints. [Registry and temporal contracts](technical-reference.md)

## Strict eligibility and evaluation

A strict episode needs unique, consistent matter and group links, a bounded conduct interval, a reviewed inventory, verified historical identity, valid independently audited critical evidence, verified publication within collection scope, applicable legal policy, and market coverage for conduct and warm-up. Record observability and unresolved linkage. Scope-specific integrity diagnostics govern acceptance of the run.

The Python preparation report currently checks inputs and audit-slot assertions only. It reports **NOT EVALUATED** as the research decision. It does not recompute strict episode eligibility, verify raw market coverage, perform legal interpretation or run any detector. Workbook formula results and the final research decision require the separate scientific checks below.

The proposed core demonstrations are statistical rules and Isolation Forest. Freeze the scored universe, primary venue rule, lookbacks, folds, matching windows, cooldown and budgets before evaluating. Keep related matters in one split, account for overlapping intervals and fit preprocessing and thresholds on eligible training data. Compare strict and hindsight training labels only when a label-dependent component can be fitted. Hold features, splits, scored observations and scoring labels fixed for that experiment.

Report known-episode recall, separately named matter and group recall, alerts per 1,000 scored instrument-sessions, alert clusters and detection timing. Retain misses in recall denominators and treat unlabeled observations as unverified. Report matter usability and episode usability as separate sample proportions. Frame-level estimates require known strata and sampling probabilities. The draft follow-up horizons of 3, 2 and 4 years measure elapsed follow-up and remain subject to freeze.

## Pilot decision

Apply the first matching condition. The thresholds below remain provisional until freeze.

| Condition | Research decision |
| --- | --- |
| Protocol still unfrozen | DRAFT |
| Required frozen configuration missing, in-scope integrity failure or failed leakage check | NOT VALID |
| Sample, review or required dependencies unfinished | IN PROGRESS, or INCOMPLETE at the deadline |
| Completed review and all pass conditions met | PASS |
| Valid completed review, at least 10 strict episodes, other feasibility conditions unmet | CONDITIONAL |
| Valid completed review, fewer than 10 strict episodes | FAIL |

PASS targets review of the agreed sample, provisionally 40 matters, with at least 20 strict episodes across at least 10 independent matter groups. It requires independent audit of all critical slots for those episodes and at least 95% valid audited required slots across the full sample. It also requires documented legal and observability states, verified identities and coverage, passing leakage checks and reproducible core baselines. A completed registry-only study can report conditional feasibility while detector validity remains unestablished.

In particular, CONDITIONAL with leakage testing **Not run** covers registry feasibility only. It cannot establish detector validity. A failed leakage test remains NOT VALID.

Record deadline delivery status separately. Unfinished delivery can be INCOMPLETE while the research decision remains DRAFT. [Acceptance scenarios](requirements/ACCEPTANCE_SCENARIOS.json)
