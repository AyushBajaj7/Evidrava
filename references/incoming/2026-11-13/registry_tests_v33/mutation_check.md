# Mutation check (can the tests fail?)
Eleven deliberate breakages of the v3.3 workbook, each run against the scenarios that should notice it. Result: all eleven caught.
| Breakage | Scenarios that failed (as they should) |
|---|---|
| Legal event with an assumed source date treated as OK (verified) | L7_source_date_only_assumed_kept_unverified, L7b_unverified_event_not_in_snapshot, L8_matter_with_only_unverified_event_not_documented |
| Unverified legal event counted as an invalid record (blocks the decision) | L7_source_date_only_assumed_kept_unverified, L8_matter_with_only_unverified_event_not_documented |
| Delay statistics use assumed first-disclosure dates again | N13_first_disclosure_not_verified_when_date_assumed |
| Gates row for episodes left out of delay statistics shows 0 | N13_first_disclosure_not_verified_when_date_assumed, DX2_no_disclosing_row_left_out |
| Included row pointing to a matter missing from Matters is not flagged | SEL1_included_matter_not_in_registry |
| Log ID without a decision is not flagged | SEL2_log_id_without_decision |
| In-scope matter without an Included log row is not flagged | SEL3_matter_without_log_entry, SEL5_draft_shown_first_errors_visible |
| Matters excluded after review wrongly demand a log row | SEL4_documented_exclusions_raise_no_error |
| Gate 4 ignores matters without a log entry | SEL3_matter_without_log_entry |
| DRAFT no longer shown first (integrity error text wins) | 01_draft_not_frozen, SEL5_draft_shown_first_errors_visible |
| Gate 4 ignores log rows pointing to unknown matters or with no decision | SEL1_included_matter_not_in_registry, SEL2_log_id_without_decision |

Earlier checks were not repeated on v3.3: the 13 breakages of v3.2 (12 caught; the one not caught is the extra test for a BLANK matter or episode link, which LibreOffice already reads as unknown) and the nine of v3.1. Their scenarios still run and pass.
