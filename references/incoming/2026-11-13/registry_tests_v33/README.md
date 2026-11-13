# Executable tests for SEBI_Episode_Registry_v3_3.xlsx
114 scenarios fill the workbook with small made-up data sets, let LibreOffice recalculate every formula, and compare the results with the outputs the design requires. Run them after ANY change to the workbook.

Need: Python 3.9+, `pip install openpyxl`, LibreOffice (set the SOFFICE variable if `soffice` is not on PATH).
Run: `python run_tests.py --workbook path\to\SEBI_Episode_Registry_v3_3.xlsx` (add `--only N12` or `--only snapshot` to run part). Exit code 0 = all met. Several minutes on one core. Do not use LibreOffice for anything else while it runs.

Files: fixtures.py (data + expected outputs), expected_outputs.json (same, readable), run_tests.py, maps.json (column letters; ties the tests to the layout), last_run_report.txt (the last full run), mutation_check.md.

Test settings (v3.2 and v3.3 defaults, decided by the project lead): availability lag 1 calendar day, evidence denominator All versions, independent auditor required. Scenarios that need other settings change them explicitly (N05, N17a).

Coverage: the six reproduced defects (D1 to D6), exact-cutoff and lag boundaries, missing warm-up data, later corrections and legal updates that must leave earlier snapshots unchanged, the v3.1 features (N01 to N18), and the v3.2 features:
- DEF1 to DEF3: the workbook's own defaults (B18 = All versions, B19 = Yes).
- N12b to N12f: first disclosure needs a valid, audited row marked "Passage discloses this episode? = Yes".
- L5 to L7: a legal event cannot be public before the verified public date of its source order; no comparison when that date is only assumed.
- ID1 to ID9: rows with data but no ID, and blank links, block the decision.
- CX0 to CX5: CONDITIONAL never overrides an integrity or leakage failure.
- L7, L7b, L8 (changed in v3.3): a legal event whose source order has only an assumed public date is kept as SOURCE DATE UNVERIFIED, is not shown in snapshots, is not counted as documented, is counted on Gates and does not block the decision by itself.
- DX0, DX2 (v3.3): delay statistics use verified first-disclosure dates only; episodes left out are counted.
- SEL1 to SEL5 (v3.3): the selection log is reconciled with Matters (unknown matter, no decision, in-scope matter without an Included row, documented exclusions, DRAFT shown first).
- C3a to C3c: the calendar-day lag, with the next-session case on a trading day and its documented limit on a non-session day.
A static check compares the Meta sheet's schema version and header hashes with maps.json.

Changed in v3.3 tests: every scenario gets one Included selection-log row per matter by default (the log is now checked); a scenario can set its own rows with data["SelLog"]. ID8 writes its stray row lower down (row 30). N13 now also expects the assumed-date episode to be left out of the delay statistics.

Changed in v3.2 tests: B1 now also moves the legal event and the last-checked date to the cutoff, because an event cannot be public before the order it cites. C1a expects 8 slots for an episode with two versions (All versions). N05 and N17a set their old defaults explicitly.

Notes: test data uses small thresholds (2 matters, 2 strict episodes); these are TEST values, not the project's 40 and 20. Expected values come from the design rules, not recorded runs. If the layout changes, maps.json must be updated and the static check will say so.
