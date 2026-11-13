# Executable tests for SEBI_Episode_Registry_v3.xlsx

These tests fill the workbook with small made-up data sets, let LibreOffice recalculate every formula,
and compare the results with the outputs the design requires. Run them after ANY change to the workbook.

## What you need
- Python 3.9 or newer, and `pip install openpyxl`
- LibreOffice (only to recalculate formulas). If `soffice` is not on your PATH, set the `SOFFICE`
  environment variable, for example on Windows:
  `set SOFFICE="C:\Program Files\LibreOffice\program\soffice.exe"`

## How to run
```
python run_tests.py --workbook path\to\SEBI_Episode_Registry_v3.xlsx
python run_tests.py --workbook ... --only D1          (one defect)
python run_tests.py --workbook ... --only snapshot    (one group)
python run_tests.py --dump-expected                   (rewrite expected_outputs.json)
```
Exit code 0 means every expectation was met. On one CPU core all 47 scenarios take about 10 minutes.
Your workbook is never changed: each scenario is saved as a separate file in `_work/`.

## Files
| File | Purpose |
|---|---|
| `fixtures.py` | The data sets (a good base, plus one change per scenario) and the expected outputs. |
| `expected_outputs.json` | The same expectations as plain JSON, for reading. |
| `run_tests.py` | The runner. |
| `maps.json` | Column letters and row numbers of the workbook. It ties the tests to the workbook layout. |
| `last_run_report.txt` | The result of the last full run. |

## What the 47 scenarios cover
| Group | Scenarios | What it proves |
|---|---|---|
| base | 00 to 04b | PASS on good data. DRAFT, NOT VALID, IN PROGRESS and INCOMPLETE states. |
| defect1_pages | D1a to D1d | Defect 1: a blank page count used to let page 99 pass. Pages must be whole numbers inside a known page count. |
| defect2_duplicates | D2 | Defect 2: duplicate episode, order and evidence IDs block evaluation and do not inflate counts. |
| defect3_strict | D3 | Defect 3: PASS used to be possible with zero strict episodes. Now it gives FAIL. |
| defect4_claim_dates | D4a, D4b | Defect 4: a claim backed only by a later order with an assumed date is not strict. CONDITIONAL also uses strict counts. |
| defect5_legal | D5 | Defect 5: a legal event without status or source is invalid and does not document the history. |
| defect6_cutoff | D6 | Defect 6: an order public after the cutoff blocks the decision. |
| boundary | B1, B2, B3a, B3b | A public date equal to the cutoff is allowed; one day later is not. Label maturity at exactly 1096 days is mature, 1095 is not. |
| warmup | W1 to W3 | Missing or partial warm-up or conduct-window market data makes an episode unusable. |
| snapshot | C0a to C2b | Availability dates are inclusive. A later correction (version 2) and a later legal update leave an earlier snapshot unchanged, and show up in later snapshots. |
| validation | V1 to V3, L1 to L4 | Duplicate version numbers, unknown episodes, whole-number version numbers, legal-event sources that must resolve to the same matter, dates and scope. |
| evidence | E1, E2 | Fourteen evidence rows with one defect each (same reviewer, wrong order, wrong page, wrong value, missing links, and more). Evidence from an order public after the cutoff never counts. |
| completion | R1, IM1 | Unresolved episodes stay in the denominator. Confirmed-unresolved slots raise review completion but never verified evidence. Independent-matter gate. |
| two_dates | DT1 | First disclosure date and label availability date are different dates. |
| estimates | ST0, ST1 | No frame-wide interval without frame sizes. The stratified estimate, standard error and interval match closed-form values. |

## Important notes
- The test data uses small thresholds (2 matters, 2 strict episodes). These are TEST values, not the project's provisional thresholds (40 and 20).
- Expected values come from the design rules on the Rules and Protocol sheets, not from recorded runs.
- Check that the tests can fail: break one formula on purpose (for example, let a blank page count pass) and run the matching scenario. It must report FAIL.
- If you change the layout (add or move columns), regenerate `maps.json` with the build script, update `fixtures.py`, and run everything again.
- To add a scenario, copy a block in `fixtures.py`: start from `base_data()`, change one thing, and list the outputs that must result.
