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
| 4. Implementation | Build checker, workload report and bounded source collection. | Runnable `check-workbook`, `screening-report` and `collect-sources` commands in Evidrava 0.3.0. |
| 5. Testing | Exercise valid/invalid inputs, missing obligations and output preservation. | Local Python tests are separate from the supplied 114-scenario formula suite. |
| 6. Local release | Package source, manifests and preparation evidence. | Local outputs; no automatic GitHub push or scientific release. |
| 7. Maintenance | Version corrections, add regressions and assess affected results. | Preserve received sources; record the impact of future protocol amendments. |

Use short iterations with one active engineering item and one annotation batch per person. Demonstrate a runnable result, inspect failures, record dependencies and select the next bounded increment. Keep scientific decisions separate from implementation choices.

## Current increment and next work

Evidrava 0.3.0 uses workbook v3.3, proposal v2.4 and the supplied tests as preserved references. The preparation checker, HTML/JSON reports, duplicate Included-matter guard and source/formula fingerprint checks are implemented. The checker never issues a research PASS and does not replace workbook recalculation or human audit. [Current preparation report](../pilot/development/evidrava-workbook/report.html)

The implemented `screening-report` checks the working copy of the fixed 30-record CSV offline. It distinguishes completed screening attempts, complete timed observations and unresolved follow-ups. The [current report](../pilot/development/evidrava-screening/report.html) shows 0 of 30 completed. Input protection and timing summaries do not replace measured human screening. [Run the exercise](../README.md#start-the-screening-exercise)

The source-collection increment acquired official PDFs for RECON-01, RECON-02 and RECON-03, preserving response bytes, hashes and page-labelled native text. These three reconnaissance documents are ready for provisional inspection; their eligibility, public dates and evidence remain unverified by humans. [Source packets](../pilot/sources/recon-first-three/report.html) · [Increment evidence](../pilot/development/evidrava-increment-2026-11-13.json)

Next, screen those first three documents and record actual screening, grouping and predecessor-search minutes. Continue through the 30-record exercise before choosing scope. Check linkage and warm-up coverage, preserve the sampling manifest, freeze before selection, and process the first five selected matters. Record researcher, reviewer, adjudication, linkage and rework time separately. Provisional extraction can continue during reviewer search; independent audit and a completed research decision remain pending. Reforecast the remaining sample from measured first-five effort.

## Engineering cap and time records

| Work | Planned maximum |
| --- | ---: |
| Small workbook/contract adjustments | 4 hours |
| Read-only checker | 8 hours |
| Negative cases, agreement checks and rerun | 5 hours |
| Draft report and handoff | 3 hours |
| **Total planned increment** | **20 active engineering hours** |

Historical work on the supplied files was not measured, so compliance with the cap cannot be claimed. The [latest development record](../pilot/development/evidrava-increment-2026-11-13.json) records implementation and validation evidence; [earlier work](../pilot/development/session-2026-11-13.json) remains preserved. Agent elapsed time is not human active-time accounting. Record future work honestly and re-plan when measured effort exceeds the allocation.

## Completion boundaries

The provisional target remains at least 20 strict usable episodes across 10 independent related-matter groups from the agreed sample, plus the audit, leakage, coverage and reproducibility conditions. Thresholds are feasibility rules, not power calculations. A completed registry-only study can support CONDITIONAL when detector validation is unfinished; failed leakage or integrity checks remain NOT VALID.

Deliver the report by 4 December with its actual research and delivery status. Reviewer delay may leave evidence unaudited and delivery incomplete; it must not be hidden by altered sign-offs or reduced denominators. [Research decisions](research-method.md#pilot-decision)
