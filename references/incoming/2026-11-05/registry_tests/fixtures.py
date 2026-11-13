"""Executable fixtures and expected outputs for SEBI_Episode_Registry_v3.xlsx.

Each scenario = a data set (the "good" base, optionally mutated) plus the outputs the workbook MUST produce.
Expected values come from the design rules in the workbook (Rules and Protocol sheets), not from recorded runs.
"""
import datetime as dt
from copy import deepcopy

D = dt.date
CUTOFF = D(2026, 10, 31)
FREEZE = D(2026, 11, 2)
ISO = lambda d: d.isoformat()


def ev(eid, matter, episode, version, field, value, order, page=4, **chg):
    row = dict(evidence_id=eid, matter_id=matter, episode_id=episode, version_id=version, field=field, value=value,
               order_id=order, page=page, locator="Para 1", confidence="High", reviewer_1="A",
               review_date_1=D(2026, 10, 20), reviewer_2="B", audit_date=D(2026, 10, 22), audit_result="Agree")
    row.update(chg)
    return row


def base_data():
    """Two matters, two episodes, one label version each, all evidence valid, 14 required slots. Expected: PASS."""
    return {
        "Rules": dict(freeze=FREEZE, cutoff=CUTOFF, target=2, pass_min=2, cond_min=1, audit_share=0.95,
                      mat_primary=3, mat_low=2, mat_high=4, min_matters=2, warmup=60),
        "Strata": [None, None, None],
        "Gates": dict(g_leak="Passing", g_base="Done", i_h1="Not run", i_deadline="No"),
        "SnapshotDate": None,
        "Matters": [
            dict(matter_id="M1", matter_name="Matter one", primary_scheme="Pump and dump", time_stratum="2021-2025",
                 review_status="Reviewed by 1 person", legal_status_current="Final order", later_checked_on=D(2026, 10, 30)),
            dict(matter_id="M2", matter_name="Matter two", primary_scheme="Price or volume ramping", time_stratum="2016-2020",
                 review_status="Audited (2nd reviewer)", legal_status_current="Interim order", later_checked_on=D(2026, 10, 30)),
        ],
        "Orders": [
            dict(order_id="O1", matter_id="M1", order_type="Interim order", order_date=D(2024, 6, 10), public_date=D(2024, 6, 14),
                 public_basis="Stated on SEBI website", total_pages=40),
            dict(order_id="O2", matter_id="M1", order_type="Final order", order_date=D(2026, 4, 8), public_date=D(2026, 4, 10),
                 public_basis="Stated on SEBI website", total_pages=60),
            dict(order_id="O3", matter_id="M2", order_type="Interim order", order_date=D(2023, 3, 1), public_date=D(2023, 3, 2),
                 public_basis="Stated on SEBI website", total_pages=30),
        ],
        "Episodes": [
            dict(episode_id="E1", matter_id="M1", instrument_name="Alpha Ltd", isin="INE111A01011", exchange="NSE",
                 segment="Main board", first_order_id="O1", mkt_conduct="Complete", mkt_warmup="Complete", ids_verified="Yes",
                 daily_informative="Yes", needs_intraday="No", needs_participant="No"),
            dict(episode_id="E2", matter_id="M2", instrument_name="Beta Ltd", isin="INE222B01022", exchange="NSE",
                 segment="Main board", first_order_id="O3", mkt_conduct="Complete", mkt_warmup="Complete", ids_verified="Yes",
                 daily_informative="Yes", needs_intraday="Yes", needs_participant="No"),
        ],
        "Versions": [
            dict(version_id="E1-v1", episode_id="E1", version_no=1, conduct_start=D(2021, 7, 14), conduct_end=D(2022, 7, 14),
                 alleged_scheme="Pump and dump"),
            dict(version_id="E2-v1", episode_id="E2", version_no=1, conduct_start=D(2022, 1, 3), conduct_end=D(2022, 3, 1),
                 alleged_scheme="Price or volume ramping"),
        ],
        "LegalStatus": [
            dict(matter_id="M1", event_date=D(2024, 6, 14), public_date=D(2024, 6, 14), status="Interim order",
                 applies_to="Whole matter", source_order_id="O1"),
            dict(matter_id="M1", event_date=D(2026, 4, 10), public_date=D(2026, 4, 10), status="Final order",
                 applies_to="Whole matter", source_order_id="O2"),
            dict(matter_id="M2", event_date=D(2023, 3, 2), public_date=D(2023, 3, 2), status="Interim order",
                 applies_to="Whole matter", source_order_id="O3"),
        ],
        "Evidence": [
            ev("V01", "M1", "E1", "E1-v1", "conduct_start", D(2021, 7, 14), "O1"),   # 0
            ev("V02", "M1", "E1", "E1-v1", "conduct_end", D(2022, 7, 14), "O1"),     # 1
            ev("V03", "M1", "E1", "E1-v1", "alleged_scheme", "Pump and dump", "O1"),  # 2
            ev("V04", "M1", "E1", None, "instrument", "Alpha Ltd", "O1"),             # 3
            ev("V05", "M1", "E1", None, "isin", "INE111A01011", "O1"),                # 4
            ev("V06", "M2", "E2", "E2-v1", "conduct_start", D(2022, 1, 3), "O3"),     # 5
            ev("V07", "M2", "E2", "E2-v1", "conduct_end", D(2022, 3, 1), "O3"),       # 6
            ev("V08", "M2", "E2", "E2-v1", "alleged_scheme", "Price or volume ramping", "O3"),  # 7
            ev("V09", "M2", "E2", None, "instrument", "Beta Ltd", "O3"),              # 8
            ev("V10", "M2", "E2", None, "isin", "INE222B01022", "O3"),                # 9
            ev("V11", "M1", None, None, "legal_status", "Final order", "O2"),          # 10
            ev("V12", "M1", None, None, "order_date", D(2024, 6, 10), "O1"),           # 11
            ev("V13", "M2", None, None, "legal_status", "Interim order", "O3"),        # 12
            ev("V14", "M2", None, None, "order_date", D(2023, 3, 1), "O3"),            # 13
        ],
    }


def large_data(n=6):
    """n matters (2 per time stratum), one episode each. Episodes in matters 4 and 6 lack warm-up data, so
    strict usable matters per stratum are k = [2, 1, 1] when n = 6."""
    data = base_data()
    for key in ("Matters", "Orders", "Episodes", "Versions", "LegalStatus", "Evidence"):
        data[key] = []
    strata = ["2011-2015", "2011-2015", "2016-2020", "2016-2020", "2021-2025", "2021-2025"]
    n_ev = 0
    for i in range(1, n + 1):
        m, o, e, v = f"M{i}", f"O{i}", f"E{i}", f"E{i}-v1"
        data["Matters"].append(dict(matter_id=m, matter_name=f"Matter {i}", primary_scheme="Pump and dump", time_stratum=strata[i - 1],
                                    review_status="Reviewed by 1 person", legal_status_current="Interim order",
                                    later_checked_on=D(2026, 10, 30)))
        data["Orders"].append(dict(order_id=o, matter_id=m, order_type="Interim order", order_date=D(2024, 6, 10),
                                   public_date=D(2024, 6, 14), public_basis="Stated on SEBI website", total_pages=40))
        warm = "Partial" if i in (4, 6) else "Complete"
        data["Episodes"].append(dict(episode_id=e, matter_id=m, instrument_name=f"Co {i} Ltd", isin=f"INE{i:03d}A01011",
                                     exchange="NSE", segment="Main board", first_order_id=o, mkt_conduct="Complete", mkt_warmup=warm,
                                     ids_verified="Yes", daily_informative="Yes", needs_intraday="No", needs_participant="No"))
        data["Versions"].append(dict(version_id=v, episode_id=e, version_no=1, conduct_start=D(2021, 7, 14),
                                     conduct_end=D(2022, 7, 14), alleged_scheme="Pump and dump"))
        data["LegalStatus"].append(dict(matter_id=m, event_date=D(2024, 6, 14), public_date=D(2024, 6, 14),
                                        status="Interim order", applies_to="Whole matter", source_order_id=o))
        rows = [(v, "conduct_start", D(2021, 7, 14)), (v, "conduct_end", D(2022, 7, 14)), (v, "alleged_scheme", "Pump and dump"),
                (None, "instrument", f"Co {i} Ltd"), (None, "isin", f"INE{i:03d}A01011")]
        for ver, fld, val in rows:
            n_ev += 1
            data["Evidence"].append(ev(f"V{n_ev:03d}", m, e, ver, fld, val, o))
        n_ev += 1
        data["Evidence"].append(ev(f"V{n_ev:03d}", m, None, None, "legal_status", "Interim order", o))
        n_ev += 1
        data["Evidence"].append(ev(f"V{n_ev:03d}", m, None, None, "order_date", D(2024, 6, 10), o))
    data["Rules"].update(target=n, min_matters=1, pass_min=1, cond_min=1)
    return data


# ------------------------------------------------------------------ expectation helpers
def decision(equals=None, startswith=None):
    return dict(type="decision", equals=equals, startswith=startswith)


def gate(name, col, equals=None, tol=1e-6):
    return dict(type="gate", name=name, col=col, equals=equals, tol=tol)


def cellx(sheet, row, key, equals):
    return dict(type="cell", sheet=sheet, row=row, key=key, equals=equals)


def snap(row, key, equals):
    return dict(type="snapshot", row=row, key=key, equals=equals)


def snapcount(equals):
    return dict(type="snapshot_count", equals=equals)


def same_snapshot(other):
    return dict(type="snapshot_same_as", scenario=other)


def mat(key, col, equals):
    return dict(type="maturity", key=key, col=col, equals=equals)


S = []  # scenarios: dict(name, group, desc, data, expect)


def scenario(name, group, desc, mutate=None, expect=(), base=None):
    data = deepcopy(base) if base is not None else base_data()
    if mutate:
        mutate(data)
    S.append(dict(name=name, group=group, desc=desc, data=data, expect=list(expect)))


# ------------------------------------------------------------------ 00 base and decision states
scenario("00_base_pass", "base", "Good data. Every gate passes.", expect=[
    decision(equals="PASS"), gate("p_total", "C", 7), gate("g_total", "C", 10), gate("g_matters", "C", 2), gate("g_usable", "C", 2),
    gate("g_indep", "C", 2), gate("g_slots", "C", 1.0), gate("g_legal", "C", 2), gate("i_strict", "C", 2), gate("i_notstrict", "C", 0),
    gate("i_unres", "C", 0), gate("i_complete", "C", 1.0), gate("i_subset", "C", 1.0), gate("i_frac", "C", 1.0),
    cellx("Episodes", 0, "strict_usable", "Yes"), cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"),
    cellx("Episodes", 0, "latest_avail_date", "2024-06-14"), cellx("Episodes", 0, "delay_days", 701),
    cellx("Episodes", 1, "delay_days", 366), cellx("Episodes", 0, "observability", "Daily-data candidate"),
    cellx("Episodes", 1, "observability", "Intraday-data dependent"), cellx("Episodes", 0, "label_mature", "Yes"),
    cellx("Versions", 0, "avail_date", "2024-06-14"), cellx("Versions", 1, "avail_date", "2023-03-02"),
    cellx("Matters", 0, "status_documented", "Yes"), cellx("Matters", 0, "n_strict", 1),
])
scenario("01_draft_not_frozen", "base", "No freeze date: the dashboard must say DRAFT.", lambda d: d["Rules"].update(freeze=None),
         [decision(startswith="DRAFT")])
scenario("02_cutoff_missing", "base", "Frozen but no cutoff: NOT VALID.", lambda d: d["Rules"].update(cutoff=None),
         [decision(startswith="NOT VALID: set the observation cutoff")])
scenario("03_leak_test_failing", "base", "A failing leak test blocks every decision.", lambda d: d["Gates"].update(g_leak="Failing"),
         [decision(startswith="NOT VALID: fix the integrity checks"), gate("p_leak", "C", "Yes")])


def m_in_progress(d):
    d["Matters"][1]["review_status"] = "Not started"


scenario("04a_in_progress", "base", "One matter unreviewed: IN PROGRESS.", m_in_progress,
         [decision(equals="IN PROGRESS (1 of 2 matters reviewed)"), cellx("Episodes", 1, "usable", "No"), gate("g_usable", "C", 1)])


def m_incomplete(d):
    m_in_progress(d)
    d["Gates"].update(i_deadline="Yes")


scenario("04b_incomplete_at_deadline", "base", "Same, deadline reached: INCOMPLETE.", m_incomplete,
         [decision(equals="INCOMPLETE (1 of 2 matters reviewed)")])

# ------------------------------------------------------------------ six defects reproduced from the review
D1_EXPECT_NOTE = "Defect 1: page loophole"


def d1a(d):
    d["Orders"][0]["total_pages"] = None
    d["Evidence"][3]["page"] = 99


scenario("D1a_blank_page_count_page_99", "defect1_pages", "DEFECT 1: an order with no page count used to let page 99 pass.", d1a, [
    cellx("Orders", 0, "order_check", "PAGES INVALID"), cellx("Evidence", 3, "source_ok", 0), cellx("Evidence", 3, "valid", 0),
    cellx("Episodes", 0, "identity_ok", "No"), cellx("Episodes", 0, "usable", "No"), decision(startswith="NOT VALID: fix the integrity checks"),
])


def d1b(d):
    d["Evidence"][3]["page"] = 99


scenario("D1b_page_beyond_known_count", "defect1_pages", "Page 99 in a 40-page order is invalid.", d1b, [
    cellx("Evidence", 3, "source_ok", 0), cellx("Evidence", 3, "valid", 0), cellx("Episodes", 0, "usable", "No"),
    gate("g_usable", "C", 1), decision(equals="CONDITIONAL"),
])


def d1c(d):
    d["Evidence"][3]["page"] = 4.5


scenario("D1c_non_integer_page", "defect1_pages", "A page number must be a whole number.", d1c, [
    cellx("Evidence", 3, "source_ok", 0), cellx("Evidence", 3, "valid", 0),
])


def d1d(d):
    d["Orders"][0]["total_pages"] = 0


scenario("D1d_zero_page_count", "defect1_pages", "A page count must be a positive whole number.", d1d, [
    cellx("Orders", 0, "order_check", "PAGES INVALID"), decision(startswith="NOT VALID"),
])


def d2(d):
    d["Episodes"].append(deepcopy(d["Episodes"][0]))
    d["Orders"].append(deepcopy(d["Orders"][0]))
    d["Evidence"][1]["evidence_id"] = d["Evidence"][0]["evidence_id"]


scenario("D2_duplicate_ids", "defect2_duplicates", "DEFECT 2: duplicate episode, order and evidence IDs must block evaluation and not inflate counts.", d2, [
    gate("p_dups", "C", 6), decision(startswith="NOT VALID: fix the integrity checks"),
    cellx("Episodes", 0, "id_status", "DUPLICATE ID"), cellx("Episodes", 0, "in_scope", "No"),
    cellx("Orders", 0, "order_check", "DUPLICATE ID"), cellx("Evidence", 0, "id_status", "DUPLICATE ID"),
    gate("g_usable", "C", 1),
])


def d3(d):
    for o in d["Orders"]:
        o["public_basis"] = "Same as order date (assumed)"


scenario("D3_all_dates_assumed_no_strict", "defect3_strict", "DEFECT 3: with zero strict episodes the old workbook still passed.", d3, [
    decision(equals="FAIL"), gate("g_usable", "C", 0), gate("i_usable", "C", 2), gate("i_notstrict", "C", 2), gate("i_strict", "C", 0),
    cellx("Episodes", 0, "usable", "Yes"), cellx("Episodes", 0, "strict_usable", "No"), cellx("Versions", 0, "avail_date", None),
])


def d4a(d):
    d["Evidence"][1]["order_id"] = "O2"
    d["Evidence"][1]["page"] = 12
    d["Orders"][1]["public_basis"] = "Same as order date (assumed)"


scenario("D4a_claim_from_later_assumed_order", "defect4_claim_dates", "DEFECT 4: a critical claim backed only by a later order with an assumed date must not be strict.", d4a, [
    cellx("Episodes", 0, "usable", "Yes"), cellx("Episodes", 0, "strict_usable", "No"), cellx("Versions", 0, "min_pub_end", None),
    gate("g_usable", "C", 1), decision(equals="CONDITIONAL"),
])


def d4b(d):
    d4a(d)
    d["Rules"].update(cond_min=2)


scenario("D4b_conditional_uses_strict_count", "defect4_claim_dates", "CONDITIONAL needs strict episodes too: 1 strict < 2 gives FAIL.", d4b, [
    gate("g_usable", "C", 1), decision(equals="FAIL"),
])


def d5(d):
    d["LegalStatus"][2]["status"] = None
    d["LegalStatus"][2]["source_order_id"] = None


scenario("D5_legal_event_without_status_or_source", "defect5_legal", "DEFECT 5: a legal event with only dates used to count as documented.", d5, [
    cellx("LegalStatus", 2, "check", "STATUS MISSING"), cellx("Matters", 1, "status_documented", "No"), gate("g_legal", "C", 1),
    decision(startswith="NOT VALID: fix the integrity checks"),
])


def d6(d):
    d["Orders"][2]["public_date"] = D(2026, 12, 1)


scenario("D6_order_public_after_cutoff", "defect6_cutoff", "DEFECT 6: an order public after the cutoff must block the decision.", d6, [
    cellx("Orders", 2, "order_check", "AFTER CUTOFF"), gate("p_after", "C", 1), cellx("Evidence", 8, "source_ok", 0),
    cellx("Evidence", 8, "valid", 0), decision(startswith="NOT VALID: fix the integrity checks"),
])

# ------------------------------------------------------------------ exact boundaries
scenario("B1_public_date_equals_cutoff", "boundary", "A public date equal to the cutoff is allowed (inclusive).",
         lambda d: d["Orders"][2].update(public_date=CUTOFF), [
    cellx("Orders", 2, "order_check", "OK"), decision(equals="PASS"), cellx("Versions", 1, "avail_date", ISO(CUTOFF)),
    cellx("Versions", 1, "avail_by_cutoff", "Yes"), cellx("Episodes", 1, "strict_usable", "Yes"),
    cellx("Episodes", 1, "first_disclosure_date", ISO(CUTOFF)),
])
scenario("B2_public_date_one_day_after_cutoff", "boundary", "One day after the cutoff blocks the decision.",
         lambda d: d["Orders"][2].update(public_date=CUTOFF + dt.timedelta(days=1)), [
    cellx("Orders", 2, "order_check", "AFTER CUTOFF"), decision(startswith="NOT VALID: fix the integrity checks"),
])


def set_e1_end(d, end):
    d["Versions"][0]["conduct_end"] = end
    d["Evidence"][1]["value"] = end


scenario("B3a_label_maturity_exact_horizon", "boundary", "Cutoff minus conduct end = 1096 days is at least 3 x 365.25 = 1095.75: mature.",
         lambda d: set_e1_end(d, CUTOFF - dt.timedelta(days=1096)), [
    cellx("Episodes", 0, "label_mature", "Yes"), mat("mat_primary", "C", 2), mat("mat_primary", "D", 2),
])
scenario("B3b_label_maturity_one_day_short", "boundary", "1095 days is below 1095.75: not mature.",
         lambda d: set_e1_end(d, CUTOFF - dt.timedelta(days=1095)), [
    cellx("Episodes", 0, "label_mature", "No"), mat("mat_primary", "C", 1), mat("mat_primary", "D", 1),
])

# ------------------------------------------------------------------ missing warm-up data
scenario("W1_warmup_partial", "warmup", "Partial warm-up data: not usable.", lambda d: d["Episodes"][1].update(mkt_warmup="Partial"), [
    cellx("Episodes", 1, "market_sufficient", "No"), cellx("Episodes", 1, "usable", "No"), cellx("Episodes", 1, "strict_usable", "No"),
    gate("g_usable", "C", 1), decision(equals="CONDITIONAL"),
])
scenario("W2_warmup_none", "warmup", "No warm-up data: not usable.", lambda d: d["Episodes"][1].update(mkt_warmup="None"), [
    cellx("Episodes", 1, "market_sufficient", "No"), cellx("Episodes", 1, "usable", "No"), decision(equals="CONDITIONAL"),
])
scenario("W3_conduct_window_partial", "warmup", "Complete warm-up but partial conduct window: not usable.",
         lambda d: d["Episodes"][1].update(mkt_conduct="Partial"), [
    cellx("Episodes", 1, "market_sufficient", "No"), cellx("Episodes", 1, "usable", "No"),
])

# ------------------------------------------------------------------ snapshots and later corrections
S0 = D(2025, 1, 1)
S2 = D(2026, 6, 1)


def snapdate(d0):
    return lambda d: d.update(SnapshotDate=d0)


scenario("C0a_snapshot_day_before_availability", "snapshot", "One day before E2's label became public: nothing available.",
         snapdate(D(2023, 3, 1)), [snapcount(0), snap(0, "label_available", "No"), snap(1, "label_available", "No"),
                                   snap(1, "version_asof", None)])
scenario("C0b_snapshot_exact_availability_day", "snapshot", "On the availability day itself the label is available (inclusive).",
         snapdate(D(2023, 3, 2)), [snapcount(1), snap(0, "label_available", "No"), snap(1, "label_available", "Yes"),
                                   snap(1, "version_asof", 1), snap(1, "conduct_end_asof", "2022-03-01"),
                                   snap(1, "legal_status_asof", "Interim order"), snap(0, "legal_status_asof", None)])
scenario("C0_snapshot_S1_reference", "snapshot", "Reference snapshot S1 = 2025-01-01 before any later correction.", snapdate(S0), [
    snapcount(2), snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), snap(0, "scheme_asof", "Pump and dump"),
    snap(0, "legal_status_asof", "Interim order"), snap(1, "version_asof", 1), snap(1, "legal_status_asof", "Interim order"),
])
scenario("C0c_snapshot_S2_before_correction", "snapshot", "Snapshot S2 = 2026-06-01 without any correction.", snapdate(S2), [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), snap(0, "legal_status_asof", "Final order"),
])


def add_correction(d):
    d["Versions"].append(dict(version_id="E1-v2", episode_id="E1", version_no=2, conduct_start=D(2021, 7, 14),
                              conduct_end=D(2022, 9, 30), alleged_scheme="Pump and dump"))
    d["Evidence"].append(ev("V15", "M1", "E1", "E1-v2", "conduct_start", D(2021, 7, 14), "O2", page=12))
    d["Evidence"].append(ev("V16", "M1", "E1", "E1-v2", "conduct_end", D(2022, 9, 30), "O2", page=12))
    d["Evidence"].append(ev("V17", "M1", "E1", "E1-v2", "alleged_scheme", "Pump and dump", "O2", page=12))


def corr_s1(d):
    add_correction(d)
    d["SnapshotDate"] = S0


scenario("C1a_later_correction_earlier_snapshot_unchanged", "snapshot",
         "A later label correction (version 2, public 2026-04-10) must leave the 2025-01-01 snapshot unchanged.", corr_s1, [
    same_snapshot("C0_snapshot_S1_reference"), snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), decision(equals="PASS"),
    cellx("Episodes", 0, "n_versions", 2), cellx("Episodes", 0, "latest_version_no", 2), cellx("Episodes", 0, "cur_end", "2022-09-30"),
    cellx("Episodes", 0, "latest_avail_date", "2026-04-10"), cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"),
    cellx("Episodes", 0, "delay_days", 701), gate("g_slots", "C", 1.0),
])


def corr_s2(d):
    add_correction(d)
    d["SnapshotDate"] = S2


scenario("C1b_later_correction_visible_later", "snapshot", "The same correction is visible in the 2026-06-01 snapshot.", corr_s2, [
    snap(0, "version_asof", 2), snap(0, "conduct_end_asof", "2022-09-30"), snap(0, "legal_status_asof", "Final order"),
])


def corr_day_before(d):
    add_correction(d)
    d["SnapshotDate"] = D(2026, 4, 9)


scenario("C1c_correction_day_before_public", "snapshot", "The day before version 2 became public, version 1 is still in force.", corr_day_before, [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"),
])


def corr_exact_day(d):
    add_correction(d)
    d["SnapshotDate"] = D(2026, 4, 10)


scenario("C1d_correction_exact_public_day", "snapshot", "On the day version 2 became public it is in force (inclusive).", corr_exact_day, [
    snap(0, "version_asof", 2), snap(0, "conduct_end_asof", "2022-09-30"),
])


def legal_update_s1(d):
    d["LegalStatus"].append(dict(matter_id="M2", event_date=D(2026, 5, 1), public_date=D(2026, 5, 2), status="Final order",
                                 applies_to="Whole matter", source_order_id="O3"))
    d["SnapshotDate"] = S0


scenario("C2a_later_legal_update_earlier_snapshot_unchanged", "snapshot", "A later legal update must leave the 2025-01-01 snapshot unchanged.", legal_update_s1, [
    same_snapshot("C0_snapshot_S1_reference"), snap(1, "legal_status_asof", "Interim order"), decision(equals="PASS"),
])


def legal_update_s2(d):
    legal_update_s1(d)
    d["SnapshotDate"] = S2


scenario("C2b_later_legal_update_visible_later", "snapshot", "The same legal update is visible in the 2026-06-01 snapshot.", legal_update_s2, [
    snap(1, "legal_status_asof", "Final order"), snap(0, "legal_status_asof", "Final order"),
])

# ------------------------------------------------------------------ versions and legal-event validation
scenario("V1_duplicate_version_number", "validation", "Two versions of one episode with the same number block evaluation.",
         lambda d: d["Versions"].append(dict(version_id="E1-v1b", episode_id="E1", version_no=1, conduct_start=D(2021, 7, 14),
                                             conduct_end=D(2022, 7, 14), alleged_scheme="Pump and dump")), [
    cellx("Versions", 0, "id_status", "DUPLICATE KEY"), cellx("Episodes", 0, "n_versions", 0), cellx("Episodes", 0, "usable", "No"),
    gate("p_dups", "C", 2), decision(startswith="NOT VALID: fix the integrity checks"),
])
scenario("V2_version_for_unknown_episode", "validation", "A version pointing at a missing episode is an invalid record.",
         lambda d: d["Versions"].append(dict(version_id="E9-v1", episode_id="E9", version_no=1, conduct_start=D(2021, 7, 14),
                                             conduct_end=D(2022, 7, 14), alleged_scheme="Pump and dump")), [
    cellx("Versions", 2, "id_status", "UNKNOWN EPISODE"), decision(startswith="NOT VALID: fix the integrity checks"),
])
scenario("V3_non_integer_version_number", "validation", "A version number must be a whole number.",
         lambda d: d["Versions"][0].update(version_no=1.5), [
    cellx("Versions", 0, "id_status", "BAD VERSION NO"), decision(startswith="NOT VALID"),
])
scenario("L1_legal_source_from_other_matter", "validation", "A legal event whose source order belongs to another matter is invalid.",
         lambda d: d["LegalStatus"][2].update(source_order_id="O1"), [
    cellx("LegalStatus", 2, "check", "SOURCE ORDER MISSING OR WRONG"), cellx("Matters", 1, "status_documented", "No"),
    decision(startswith="NOT VALID: fix the integrity checks"),
])
scenario("L2_legal_public_before_event", "validation", "An event cannot become public before it happens.",
         lambda d: d["LegalStatus"][0].update(public_date=D(2024, 6, 13)), [
    cellx("LegalStatus", 0, "check", "PUBLIC BEFORE EVENT"), decision(startswith="NOT VALID"),
])
scenario("L3_specific_episode_event_without_episode", "validation", "A specific-episode event needs an episode of the same matter.",
         lambda d: d["LegalStatus"][0].update(applies_to="Specific episode", episode_id=None), [
    cellx("LegalStatus", 0, "check", "EPISODE MISSING OR WRONG"), decision(startswith="NOT VALID"),
])
scenario("L4_last_checked_before_latest_event", "validation", "A last-checked date older than the latest event does not document the history.",
         lambda d: d["Matters"][0].update(later_checked_on=D(2025, 1, 1)), [
    cellx("Matters", 0, "status_documented", "No"), gate("g_legal", "C", 1), decision(equals="CONDITIONAL"),
])


# ------------------------------------------------------------------ evidence probes
def probes(d):
    base = dict(matter_id="M1", episode_id="E1", version_id=None, field="isin", value="INE111A01011", order_id="O1", page=4)
    rows = [
        ("P01_same_reviewer", dict(reviewer_2="a")),
        ("P02_order_of_other_matter", dict(field="conduct_start", value=D(2021, 7, 14), version_id="E1-v1", order_id="O3")),
        ("P03_page_too_high", dict(page=99)),
        ("P04_value_mismatch", dict(value="INE999Z99999")),
        ("P05_no_episode_id", dict(episode_id=None)),
        ("P06_audit_before_review", dict(audit_date=D(2026, 10, 10))),
        ("P07_not_audited", dict(audit_result="Not audited")),
        ("P08_blank_locator", dict(locator="")),
        ("P09_episode_of_other_matter", dict(episode_id="E2")),
        ("P10_non_slot_field", dict(field="observability", value="free text")),
        ("P11_version_field_without_version", dict(field="conduct_start", value=D(2021, 7, 14), version_id=None)),
        ("P12_version_of_other_episode", dict(field="conduct_start", value=D(2021, 7, 14), version_id="E2-v1")),
        ("P13_confirmed_unresolved", dict(audit_result="Confirmed unresolved")),
        ("P14_non_integer_page", dict(page=4.5)),
    ]
    for eid, chg in rows:
        r = dict(base); r.update(chg)
        d["Evidence"].append(ev(eid, r["matter_id"], r["episode_id"], r["version_id"], r["field"], r["value"], r["order_id"],
                                page=r["page"], **{k: v for k, v in chg.items() if k in ("reviewer_2", "audit_date", "audit_result", "locator")}))


exp = [decision(equals="PASS"), gate("g_slots", "C", 1.0)]
for i in range(14):                                   # base evidence rows stay valid
    exp.append(cellx("Evidence", i, "valid", 1))
for i, valid in enumerate([0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]):
    exp.append(cellx("Evidence", 14 + i, "valid", valid))
exp += [cellx("Evidence", 14 + 9, "required", "No"), cellx("Evidence", 14 + 12, "unresolved_ok", 1), cellx("Evidence", 14, "review_ok", 0),
        cellx("Evidence", 14 + 1, "source_ok", 0), cellx("Evidence", 14 + 2, "source_ok", 0), cellx("Evidence", 14 + 3, "value_matches", 0),
        cellx("Evidence", 14 + 4, "scope_ok", 0), cellx("Evidence", 14 + 8, "scope_ok", 0), cellx("Evidence", 14 + 10, "scope_ok", 0),
        cellx("Evidence", 14 + 11, "scope_ok", 0), cellx("Evidence", 14 + 13, "source_ok", 0)]
scenario("E1_evidence_probes", "evidence", "Fourteen extra evidence rows, each with one defect. Only the non-slot control row is valid; the base slots stay at 100%.", probes, exp)


def late_order(d):
    d["Orders"].append(dict(order_id="O5", matter_id="M1", order_type="Final order", order_date=D(2026, 11, 10),
                            public_date=D(2026, 11, 15), public_basis="Stated on SEBI website", total_pages=20))
    d["Evidence"].append(ev("V90", "M1", "E1", None, "isin", "INE111A01011", "O5", page=3))


scenario("E2_evidence_from_order_after_cutoff", "evidence", "Evidence citing an order made public after the cutoff never counts, and the order blocks the decision.", late_order, [
    cellx("Orders", 3, "order_check", "AFTER CUTOFF"), cellx("Evidence", 14, "source_ok", 0), cellx("Evidence", 14, "valid", 0),
    decision(startswith="NOT VALID: fix the integrity checks"),
])


# ------------------------------------------------------------------ completion, independence, two dates, estimates
def unresolved(d):
    d["Episodes"].append(dict(episode_id="E3", matter_id="M1", instrument_name="Gamma Ltd", exchange="NSE", segment="Main board",
                              mkt_conduct="None", mkt_warmup="None", ids_verified="No"))
    d["Versions"].append(dict(version_id="E3-v1", episode_id="E3", version_no=1, conduct_start=D(2022, 1, 3),
                              conduct_end=D(2022, 3, 1), alleged_scheme="Pump and dump"))
    d["Evidence"].append(ev("U1", "M1", "E3", None, "isin", None, None, page=None, audit_result="Confirmed unresolved"))
    d["Evidence"].append(ev("U2", "M1", "E3", "E3-v1", "conduct_start", None, None, page=None, audit_result="Confirmed unresolved"))


scenario("R1_review_completion_vs_verified", "completion", "An unresolved episode stays in the denominator. Confirmed-unresolved slots raise review completion, never verified evidence.", unresolved, [
    gate("g_slots", "C", 14 / 19), gate("i_complete", "C", 16 / 19), gate("i_subset", "C", 1.0), gate("i_unres", "C", 1),
    cellx("Episodes", 2, "slots_expected_total", 5), cellx("Episodes", 2, "slots_valid_total", 0), cellx("Episodes", 2, "slots_done_total", 2),
    cellx("Episodes", 2, "usable", "No"), gate("g_obs", "D", "NOT YET"), decision(equals="CONDITIONAL"),
    cellx("Evidence", 14, "valid", 0), cellx("Evidence", 14, "unresolved_ok", 1), cellx("Evidence", 15, "unresolved_ok", 1),
])
scenario("IM1_too_few_independent_matters", "completion", "Two strict episodes from two matters, but three matters are required.",
         lambda d: d["Rules"].update(min_matters=3), [
    gate("g_indep", "C", 2), gate("g_indep", "D", "NOT YET"), decision(equals="CONDITIONAL"),
])
scenario("DT1_two_publication_dates", "two_dates", "First disclosure (2024-06-14) differs from label availability (2026-04-10) when conduct_end is only public in the final order.",
         lambda d: d["Evidence"][1].update(order_id="O2", page=12), [
    cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Episodes", 0, "latest_avail_date", "2026-04-10"),
    cellx("Episodes", 0, "delay_days", 701), cellx("Episodes", 0, "strict_usable", "Yes"), cellx("Versions", 0, "min_pub_end", "2026-04-10"),
    cellx("Versions", 0, "min_pub_start", "2024-06-14"), decision(equals="PASS"),
])


def large_strata(frame=True):
    def f(d):
        if frame:
            d["Strata"] = [100, 200, 300]
    return f


def strat_expect(frame):
    n_h, k_h = [2, 2, 2], [2, 1, 1]
    out = [gate("i_frac", "C", 4 / 6), dict(type="stratum", row=0, col="C", equals=2), dict(type="stratum", row=1, col="D", equals=1)]
    if not frame:
        out += [gate("est", "C", "n/a"), gate("lo", "C", "n/a")]
        return out
    N = [100, 200, 300]
    W = [x / sum(N) for x in N]
    p = [k / n for k, n in zip(k_h, n_h)]
    est = sum(w * pp for w, pp in zip(W, p))
    var = sum((w ** 2) * (1 - n / Nn) * pp * (1 - pp) / (n - 1) for w, n, Nn, pp in zip(W, n_h, N, p))
    se = var ** 0.5
    out += [gate("est", "C", est, 1e-6), gate("se", "C", se, 1e-6), gate("lo", "C", max(0.0, est - 1.96 * se), 1e-6),
            gate("hi", "C", min(1.0, est + 1.96 * se), 1e-6)]
    return out


scenario("ST0_no_frame_sizes_no_interval", "estimates", "Without frame sizes there is a sample fraction but no frame-wide estimate or interval.",
         large_strata(False), strat_expect(False), base=large_data(6))
scenario("ST1_stratified_estimate", "estimates", "With frame sizes 100, 200, 300 the stratified estimate, SE and interval match the closed-form values.",
         large_strata(True), strat_expect(True), base=large_data(6))


def jsonable():
    """Scenario list with dates converted for expected_outputs.json (data omitted)."""
    return [dict(name=s["name"], group=s["group"], description=s["desc"], expect=s["expect"]) for s in S]
