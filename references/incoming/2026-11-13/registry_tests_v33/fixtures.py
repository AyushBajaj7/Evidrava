"""Executable fixtures and expected outputs for SEBI_Episode_Registry_v3_3.xlsx.

Each scenario = a data set (the "good" base, optionally changed) plus the outputs the workbook MUST produce.
Expected values come from the design rules in the workbook (Rules and Protocol sheets), not from recorded runs.
Test settings: availability lag 1, evidence denominator "All versions", independent auditor required
(the v3.2 defaults, decided by the project lead). Scenarios that test other settings change them explicitly.
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
               review_date_1=D(2026, 10, 20), reviewer_2="B", audit_date=D(2026, 10, 22), audit_result="Agree",
               discloses=("Yes" if field in ("conduct_start", "conduct_end", "alleged_scheme") else None))
    row.update(chg)
    return row


def base_data():
    """Two matters, two episodes, one label version each, all evidence valid, 14 required slots. Expected: PASS."""
    return {
        "Rules": dict(freeze=FREEZE, cutoff=CUTOFF, target=2, pass_min=2, cond_min=1, audit_share=0.95,
                      mat_primary=3, mat_low=2, mat_high=4, min_matters=2, warmup=60,
                      lag=1, denom="All versions", indep="Yes"),
        "Strata": [None, None, None],
        "Gates": dict(g_leak="Passing", g_base="Done", i_h1="Not run", i_deadline="No"),
        "SnapshotDate": None,
        "Raw": [],
        "People": [
            dict(name="A", role="Project lead", independent="No"),
            dict(name="B", role="Reviewer", independent="Yes"),
        ],
        "Matters": [
            dict(matter_id="M1", matter_name="Matter one", primary_scheme="Pump and dump", time_stratum="2021-2025",
                 review_status="Reviewed by 1 person", legal_status_current="Final order", later_checked_on=D(2026, 10, 30),
                 group_id="G1", group_reviewed="Yes", inventory_complete="Yes"),
            dict(matter_id="M2", matter_name="Matter two", primary_scheme="Price or volume ramping", time_stratum="2016-2020",
                 review_status="Audited (2nd reviewer)", legal_status_current="Interim order", later_checked_on=D(2026, 10, 30),
                 group_id="G2", group_reviewed="Yes", inventory_complete="Yes"),
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
                 segment="Main board", mkt_conduct="Complete", mkt_warmup="Complete", ids_verified="Yes",
                 daily_informative="Yes", needs_intraday="No", needs_participant="No"),
            dict(episode_id="E2", matter_id="M2", instrument_name="Beta Ltd", isin="INE222B01022", exchange="NSE",
                 segment="Main board", mkt_conduct="Complete", mkt_warmup="Complete", ids_verified="Yes",
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


def default_sellog(data):
    """One Included selection-log row per matter. Scenarios that test the log set data["SelLog"] themselves."""
    return [dict(log_id=f"L{i + 1}", decision="Included", matter_id=x["matter_id"])
            for i, x in enumerate(x for x in data["Matters"] if x.get("matter_id"))]


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
                                    later_checked_on=D(2026, 10, 30), group_id=f"G{i}", group_reviewed="Yes",
                                    inventory_complete="Yes"))
        data["Orders"].append(dict(order_id=o, matter_id=m, order_type="Interim order", order_date=D(2024, 6, 10),
                                   public_date=D(2024, 6, 14), public_basis="Stated on SEBI website", total_pages=40))
        warm = "Partial" if i in (4, 6) else "Complete"
        data["Episodes"].append(dict(episode_id=e, matter_id=m, instrument_name=f"Co {i} Ltd", isin=f"INE{i:03d}A01011",
                                     exchange="NSE", segment="Main board", mkt_conduct="Complete", mkt_warmup=warm,
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


def cellref(sheet, ref, equals):
    return dict(type="cellref", sheet=sheet, ref=ref, equals=equals)


def mat(key, col, equals):
    return dict(type="maturity", key=key, col=col, equals=equals)


S = []  # scenarios


def scenario(name, group, desc, mutate=None, expect=(), base=None):
    data = deepcopy(base) if base is not None else base_data()
    if mutate:
        mutate(data)
    S.append(dict(name=name, group=group, desc=desc, data=data, expect=list(expect)))


# ------------------------------------------------------------------ 00 base and decision states
scenario("00_base_pass", "base", "Good data. Every gate passes.", expect=[
    decision(equals="PASS"), gate("p_total", "C", 8), gate("g_total", "C", 10), gate("g_matters", "C", 2), gate("g_usable", "C", 2),
    gate("g_indep", "C", 2), gate("g_slots", "C", 1.0), gate("g_legal", "C", 2), gate("i_strict", "C", 2), gate("i_notstrict", "C", 0),
    gate("i_unres", "C", 0), gate("i_complete", "C", 1.0), gate("i_subset", "C", 1.0), gate("i_frac", "C", 1.0),
    gate("i_indep_share", "C", 1.0), gate("i_inventory", "C", 2),
    cellx("Episodes", 0, "strict_usable", "Yes"), cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"),
    cellx("Episodes", 0, "disclosure_verified", "Yes"), cellx("Episodes", 0, "latest_avail_date", "2024-06-14"),
    cellx("Episodes", 0, "delay_days", 701), cellx("Episodes", 1, "delay_days", 366),
    cellx("Episodes", 0, "slots_expected_total", 5), cellx("Episodes", 0, "observability", "Daily-data candidate"),
    cellx("Episodes", 1, "observability", "Intraday-data dependent"), cellx("Episodes", 0, "label_mature", "Yes"),
    cellx("Versions", 0, "avail_date", "2024-06-14"), cellx("Versions", 1, "avail_date", "2023-03-02"),
    cellx("Versions", 0, "min_pub_scheme", "2024-06-14"),
    cellx("Matters", 0, "status_documented", "Yes"), cellx("Matters", 0, "n_strict", 1), cellx("Matters", 0, "group_first_strict", 1),
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
def d1a(d):
    d["Orders"][0]["total_pages"] = None
    d["Evidence"][3]["page"] = 99


scenario("D1a_blank_page_count_page_99", "defect1_pages", "DEFECT 1: an order with no page count used to let page 99 pass.", d1a, [
    cellx("Orders", 0, "order_check", "PAGES INVALID"), cellx("Evidence", 3, "source_ok", 0), cellx("Evidence", 3, "valid", 0),
    cellx("Episodes", 0, "identity_ok", "No"), cellx("Episodes", 0, "usable", "No"), decision(startswith="NOT VALID: fix the integrity checks"),
])


def d1b(d):
    d["Evidence"][3]["page"] = 99


scenario("D1b_page_beyond_known_count", "defect1_pages", "Page 99 in a 40-page order is invalid. The review is then not complete.", d1b, [
    cellx("Evidence", 3, "source_ok", 0), cellx("Evidence", 3, "valid", 0), cellx("Episodes", 0, "usable", "No"),
    gate("g_usable", "C", 1), decision(startswith="IN PROGRESS (review not complete"),
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
def b1(d):
    d["Orders"][2].update(public_date=CUTOFF)
    # the legal event that cites this order cannot be public before the order (v3.2), so it moves to the cutoff too
    d["LegalStatus"][2].update(event_date=CUTOFF, public_date=CUTOFF)
    d["Matters"][1].update(later_checked_on=CUTOFF)


scenario("B1_public_date_equals_cutoff", "boundary", "A public date equal to the cutoff is allowed (inclusive).",
         b1, [
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

# ------------------------------------------------------------------ snapshots, lag and later corrections
S0 = D(2025, 1, 1)
S2 = D(2026, 6, 1)


def snapdate(d0, lag=None):
    def f(d):
        d["SnapshotDate"] = d0
        if lag is not None:
            d["Rules"]["lag"] = lag
    return f


scenario("C0a_snapshot_day_before_availability", "snapshot", "One day before E2's label became public: nothing available.",
         snapdate(D(2023, 3, 1)), [snapcount(0), snap(0, "label_available", "No"), snap(1, "label_available", "No"),
                                   snap(1, "version_asof", None)])
scenario("C0b_lag0_exact_availability_day", "snapshot", "LAG 0: on the availability day itself the label is available.",
         snapdate(D(2023, 3, 2), lag=0), [snapcount(1), snap(0, "label_available", "No"), snap(1, "label_available", "Yes"),
                                          snap(1, "version_asof", 1), snap(1, "conduct_end_asof", "2022-03-01"),
                                          snap(1, "matter_status_asof", "Interim order"), snap(0, "matter_status_asof", None)])
scenario("C0b_lag1_exact_availability_day", "snapshot", "LAG 1 (default): on the availability day itself nothing is available yet.",
         snapdate(D(2023, 3, 2)), [snapcount(0), snap(1, "label_available", "No"), snap(1, "version_asof", None),
                                   snap(1, "matter_status_asof", None)])
scenario("C0b_lag1_day_after_availability", "snapshot", "LAG 1: the day after, the label and the legal status are available.",
         snapdate(D(2023, 3, 3)), [snapcount(1), snap(1, "label_available", "Yes"), snap(1, "version_asof", 1),
                                   snap(1, "matter_status_asof", "Interim order")])
scenario("C0_snapshot_S1_reference", "snapshot", "Reference snapshot S1 = 2025-01-01 before any later correction.", snapdate(S0), [
    snapcount(2), snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), snap(0, "scheme_asof", "Pump and dump"),
    snap(0, "matter_status_asof", "Interim order"), snap(0, "episode_status_asof", None),
    snap(1, "version_asof", 1), snap(1, "matter_status_asof", "Interim order"),
])
scenario("C0c_snapshot_S2_before_correction", "snapshot", "Snapshot S2 = 2026-06-01 without any correction.", snapdate(S2), [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), snap(0, "matter_status_asof", "Final order"),
])


def add_correction(d):
    d["Versions"].append(dict(version_id="E1-v2", episode_id="E1", version_no=2, conduct_start=D(2021, 7, 14),
                              conduct_end=D(2022, 9, 30), alleged_scheme="Pump and dump"))
    d["Evidence"].append(ev("V15", "M1", "E1", "E1-v2", "conduct_start", D(2021, 7, 14), "O2", page=12))
    d["Evidence"].append(ev("V16", "M1", "E1", "E1-v2", "conduct_end", D(2022, 9, 30), "O2", page=12))
    d["Evidence"].append(ev("V17", "M1", "E1", "E1-v2", "alleged_scheme", "Pump and dump", "O2", page=12))


def corr(d0, lag=None):
    def f(d):
        add_correction(d)
        d["SnapshotDate"] = d0
        if lag is not None:
            d["Rules"]["lag"] = lag
    return f


scenario("C1a_later_correction_earlier_snapshot_unchanged", "snapshot",
         "A later label correction (version 2, public 2026-04-10) must leave the 2025-01-01 snapshot unchanged.", corr(S0), [
    same_snapshot("C0_snapshot_S1_reference"), snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), decision(equals="PASS"),
    cellx("Episodes", 0, "n_versions", 2), cellx("Episodes", 0, "latest_version_no", 2), cellx("Episodes", 0, "cur_end", "2022-09-30"),
    cellx("Episodes", 0, "latest_avail_date", "2026-04-10"), cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"),
    cellx("Episodes", 0, "delay_days", 701), cellx("Episodes", 0, "slots_expected_total", 8), gate("g_slots", "C", 1.0),
])
scenario("C1b_later_correction_visible_later", "snapshot", "The same correction is visible in the 2026-06-01 snapshot.", corr(S2), [
    snap(0, "version_asof", 2), snap(0, "conduct_end_asof", "2022-09-30"), snap(0, "matter_status_asof", "Final order"),
])
scenario("C1c_correction_day_before_public", "snapshot", "The day before version 2 became public, version 1 is still in force.", corr(D(2026, 4, 9)), [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"),
])
scenario("C1d_lag0_correction_exact_public_day", "snapshot", "LAG 0: on the day version 2 became public it is in force.", corr(D(2026, 4, 10), lag=0), [
    snap(0, "version_asof", 2), snap(0, "conduct_end_asof", "2022-09-30"),
])
scenario("C1e_lag1_correction_exact_public_day", "snapshot", "LAG 1: on the public day version 1 is still in force.", corr(D(2026, 4, 10)), [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"),
])
scenario("C1f_lag1_correction_day_after", "snapshot", "LAG 1: the day after, version 2 is in force.", corr(D(2026, 4, 11)), [
    snap(0, "version_asof", 2), snap(0, "conduct_end_asof", "2022-09-30"),
])


def legal_update(d0):
    def f(d):
        d["LegalStatus"].append(dict(matter_id="M2", event_date=D(2026, 5, 1), public_date=D(2026, 5, 2), status="Final order",
                                     applies_to="Whole matter", source_order_id="O3"))
        d["SnapshotDate"] = d0
    return f


scenario("C2a_later_legal_update_earlier_snapshot_unchanged", "snapshot", "A later legal update must leave the 2025-01-01 snapshot unchanged.", legal_update(S0), [
    same_snapshot("C0_snapshot_S1_reference"), snap(1, "matter_status_asof", "Interim order"), decision(equals="PASS"),
])
scenario("C2b_later_legal_update_visible_later", "snapshot", "The same legal update is visible in the 2026-06-01 snapshot.", legal_update(S2), [
    snap(1, "matter_status_asof", "Final order"), snap(0, "matter_status_asof", "Final order"),
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
        ("P15_reviewer_not_on_people_sheet", dict(reviewer_2="Zed")),
    ]
    for eid, chg in rows:
        r = dict(base); r.update(chg)
        d["Evidence"].append(ev(eid, r["matter_id"], r["episode_id"], r["version_id"], r["field"], r["value"], r["order_id"],
                                page=r["page"], **{k: v for k, v in chg.items() if k in ("reviewer_2", "audit_date", "audit_result", "locator")}))


exp = [decision(equals="PASS"), gate("g_slots", "C", 1.0)]
for i in range(14):
    exp.append(cellx("Evidence", i, "valid", 1))
valid_flags = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
for i, valid in enumerate(valid_flags):
    exp.append(cellx("Evidence", 14 + i, "valid", valid))
exp += [cellx("Evidence", 14 + 9, "required", "No"), cellx("Evidence", 14 + 12, "unresolved_ok", 1), cellx("Evidence", 14, "review_ok", 0),
        cellx("Evidence", 14 + 1, "source_ok", 0), cellx("Evidence", 14 + 2, "source_ok", 0), cellx("Evidence", 14 + 3, "value_matches", 0),
        cellx("Evidence", 14 + 4, "scope_ok", 0), cellx("Evidence", 14 + 8, "scope_ok", 0), cellx("Evidence", 14 + 10, "scope_ok", 0),
        cellx("Evidence", 14 + 11, "scope_ok", 0), cellx("Evidence", 14 + 13, "source_ok", 0),
        cellx("Evidence", 14 + 14, "reviewers_listed", 0), cellx("Evidence", 14 + 14, "review_ok", 0)]
scenario("E1_evidence_probes", "evidence", "Fifteen extra evidence rows, each with one defect. Only the non-slot control row is valid; the base slots stay at 100%.", probes, exp)


def late_order(d):
    d["Orders"].append(dict(order_id="O5", matter_id="M1", order_type="Final order", order_date=D(2026, 11, 10),
                            public_date=D(2026, 11, 15), public_basis="Stated on SEBI website", total_pages=20))
    d["Evidence"].append(ev("V90", "M1", "E1", None, "isin", "INE111A01011", "O5", page=3))


scenario("E2_evidence_from_order_after_cutoff", "evidence", "Evidence citing an order made public after the cutoff never counts, and the order blocks the decision.", late_order, [
    cellx("Orders", 3, "order_check", "AFTER CUTOFF"), cellx("Evidence", 14, "source_ok", 0), cellx("Evidence", 14, "valid", 0),
    decision(startswith="NOT VALID: fix the integrity checks"),
])


# ------------------------------------------------------------------ completion, independence, two dates, estimates
def unresolved(rows):
    def f(d):
        d["Episodes"].append(dict(episode_id="E3", matter_id="M1", instrument_name="Gamma Ltd", exchange="NSE", segment="Main board",
                                  mkt_conduct="None", mkt_warmup="None", ids_verified="No"))
        d["Versions"].append(dict(version_id="E3-v1", episode_id="E3", version_no=1, conduct_start=D(2022, 1, 3),
                                  conduct_end=D(2022, 3, 1), alleged_scheme="Pump and dump"))
        allrows = [("U1", None, "isin"), ("U2", "E3-v1", "conduct_start"), ("U3", None, "instrument"),
                   ("U4", "E3-v1", "conduct_end"), ("U5", "E3-v1", "alleged_scheme")]
        for uid, ver, fld in allrows[:rows]:
            d["Evidence"].append(ev(uid, "M1", "E3", ver, fld, None, None, page=None, audit_result="Confirmed unresolved"))
    return f


scenario("R1_all_slots_done_one_unresolved_episode", "completion",
         "An unresolved episode stays in the denominator. All its slots are confirmed unresolved: review is complete, verified share is 14/19.", unresolved(5), [
    gate("g_slots", "C", 14 / 19), gate("i_complete", "C", 1.0), gate("i_subset", "C", 1.0), gate("i_unres", "C", 1),
    cellx("Episodes", 2, "slots_expected_total", 5), cellx("Episodes", 2, "slots_valid_total", 0), cellx("Episodes", 2, "slots_done_total", 5),
    cellx("Episodes", 2, "usable", "No"), gate("g_obs", "D", "NOT YET"), decision(equals="CONDITIONAL"),
    cellx("Evidence", 14, "valid", 0), cellx("Evidence", 14, "unresolved_ok", 1), cellx("Evidence", 15, "unresolved_ok", 1),
])
scenario("R2_only_two_slots_done", "completion", "Only two of E3's five slots are confirmed unresolved: the review is not complete, so no final decision.", unresolved(2), [
    gate("g_slots", "C", 14 / 19), gate("i_complete", "C", 16 / 19), decision(startswith="IN PROGRESS (review not complete: 84%"),
])
scenario("IM1_too_few_independent_groups", "completion", "Two strict episodes from two groups, but three groups are required.",
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

# ================================================================== NEW IN v3.1
# ---- 1 independent groups
scenario("N01_two_matters_one_group", "v31_groups", "Two matters in one related-matter group count as ONE independent group.",
         lambda d: d["Matters"][1].update(group_id="G1"), [
    gate("g_indep", "C", 1), cellx("Matters", 0, "group_first_strict", 1), cellx("Matters", 1, "group_first_strict", 0),
    decision(equals="CONDITIONAL"),
])
scenario("N02_group_not_reviewed", "v31_groups", "A group that no second person reviewed counts for nothing.",
         lambda d: d["Matters"][1].update(group_reviewed="No"), [
    gate("g_indep", "C", 1), cellx("Matters", 1, "group_first_strict", 0), decision(equals="CONDITIONAL"),
])
scenario("N03_blank_group_defaults_to_own_id", "v31_groups", "A blank group is the matter's own ID (a reviewed singleton).",
         lambda d: d["Matters"][1].update(group_id=None), [
    cellx("Matters", 1, "group_key", "M2"), gate("g_indep", "C", 2), decision(equals="PASS"),
])
# ---- 2 reviewer registry and independence
scenario("N04_reviewer_not_on_people_sheet", "v31_people", "An unlisted auditor makes the row invalid, so the slot is neither audited nor unresolved.",
         lambda d: d["Evidence"][3].update(reviewer_2="Zed"), [
    cellx("Evidence", 3, "reviewers_listed", 0), cellx("Evidence", 3, "valid", 0), decision(startswith="IN PROGRESS (review not complete"),
])
def indep_off(d):
    d["Rules"]["indep"] = "No"
    d["People"][1].update(independent="No")


scenario("N05_independence_optional_when_set_to_no", "v31_people", "B19 set to No: a non-independent auditor is accepted and the share is only reported.",
         indep_off, [
    decision(equals="PASS"), gate("i_indep_share", "C", 0.0), cellx("Evidence", 0, "auditor_independent", "No"), cellx("Evidence", 0, "valid", 1),
])


def indep_required(auditor_independent):
    def f(d):
        d["Rules"]["indep"] = "Yes"
        d["People"][1]["independent"] = "Yes" if auditor_independent else "No"
    return f


scenario("N06_independence_required_not_met", "v31_people", "B19 = Yes and the auditor is not independent: no evidence counts, the review is not complete.",
         indep_required(False), [cellx("Evidence", 0, "valid", 0), gate("i_complete", "C", 0.0), decision(startswith="IN PROGRESS (review not complete: 0%")])
scenario("N07_independence_required_met", "v31_people", "B19 = Yes with an independent auditor: PASS and the independent share is 100%.",
         indep_required(True), [decision(equals="PASS"), gate("i_indep_share", "C", 1.0)])
scenario("N08_people_duplicate_name", "v31_people", "A duplicate name on the People sheet blocks the decision.",
         lambda d: d["People"].append(dict(name="A", role="Duplicate", independent="No")), [
    gate("p_dups", "C", 2), cellx("People", 0, "id_check", "DUPLICATE ID"), decision(startswith="NOT VALID: fix the integrity checks"),
])
# ---- 3 review readiness
scenario("N09a_empty_slot_not_ready", "v31_readiness", "A required slot with no evidence and no unresolved confirmation: no final decision yet.",
         lambda d: d["Evidence"].pop(4), [
    decision(startswith="IN PROGRESS (review not complete"), gate("g_slots", "C", 13 / 14), gate("i_complete", "C", 13 / 14),
])


def empty_slot_deadline(d):
    d["Evidence"].pop(4)
    d["Gates"]["i_deadline"] = "Yes"


scenario("N09b_empty_slot_at_deadline", "v31_readiness", "Same at the deadline: INCOMPLETE (review).", empty_slot_deadline, [
    decision(startswith="INCOMPLETE (review not complete"),
])
scenario("N10_episode_list_not_complete", "v31_readiness", "A matter whose episode list is not marked complete blocks the final decision.",
         lambda d: d["Matters"][0].update(inventory_complete="No"), [
    gate("i_inventory", "C", 1), gate("i_inventory", "B", 2), gate("i_complete", "C", 1.0),
    decision(startswith="IN PROGRESS (review not complete: 100% of required slots done; 1 of 2 matters"),
])
# ---- 4 scheme availability


def scheme_late(snapshot_date):
    def f(d):
        d["Evidence"][2].update(order_id="O2", page=12)
        d["SnapshotDate"] = snapshot_date
    return f


scenario("N11a_scheme_hidden_until_its_evidence_is_public", "v31_scheme",
         "Conduct dates are public in 2024 but the scheme only in the 2026 order: the 2025 snapshot shows no scheme.", scheme_late(S0), [
    snap(0, "version_asof", 1), snap(0, "conduct_end_asof", "2022-07-14"), snap(0, "scheme_asof", None),
    cellx("Versions", 0, "min_pub_scheme", "2026-04-10"), cellx("Episodes", 0, "latest_avail_date", "2024-06-14"),
    cellx("Episodes", 0, "strict_usable", "Yes"), decision(equals="PASS"),
])
scenario("N11b_scheme_visible_later", "v31_scheme", "After the scheme evidence became public (plus lag) the scheme is shown.", scheme_late(S2), [
    snap(0, "scheme_asof", "Pump and dump"),
])
scenario("N11c_scheme_lag1_on_public_day", "v31_scheme", "LAG 1: on the day the scheme evidence became public it is still hidden.", scheme_late(D(2026, 4, 10)), [
    snap(0, "scheme_asof", None), snap(0, "version_asof", 1),
])
scenario("N11d_scheme_lag1_day_after", "v31_scheme", "LAG 1: the day after, it is shown.", scheme_late(D(2026, 4, 11)), [
    snap(0, "scheme_asof", "Pump and dump"),
])


# ---- 5 first disclosure from evidence
def unrelated_earlier_order(d):
    d["Orders"].append(dict(order_id="O0", matter_id="M1", order_type="Show-cause notice (public)", order_date=D(2024, 1, 1),
                            public_date=D(2024, 1, 2), public_basis="Stated on SEBI website", total_pages=10))


scenario("N12_unrelated_earlier_order_is_not_first_disclosure", "v31_disclosure",
         "An earlier order with no evidence row about the episode does not become its first disclosure.", unrelated_earlier_order, [
    cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Episodes", 0, "delay_days", 701), decision(equals="PASS"),
])
scenario("N13_first_disclosure_not_verified_when_date_assumed", "v31_disclosure",
         "If the earliest evidence order has only an assumed public date, the first disclosure date is flagged unverified.",
         lambda d: d["Orders"][0].update(public_basis="Same as order date (assumed)"), [
    cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Episodes", 0, "disclosure_verified", "No"),
    cellx("Episodes", 0, "delay_days", None), gate("d_count", "B", 1), gate("d_excl", "B", 1), gate("d_median", "B", 366),
])


# ---- 6 legal events by scope
def episode_event(d0):
    def f(d):
        d["LegalStatus"].append(dict(matter_id="M1", event_date=D(2025, 3, 1), public_date=D(2025, 3, 2), status="Modified on appeal",
                                     applies_to="Specific episode", episode_id="E1", source_order_id="O1"))
        d["SnapshotDate"] = d0
    return f


scenario("N14_episode_event_earlier_snapshot_unchanged", "v31_scope", "An episode-scoped event dated 2025-03-02 does not change the 2025-01-01 snapshot.",
         episode_event(S0), [same_snapshot("C0_snapshot_S1_reference"), decision(equals="PASS")])
scenario("N15_episode_event_shown_for_its_episode_only", "v31_scope",
         "Later, E1 shows its own episode status next to the whole-matter status; E2 shows none. Conflicts are preserved.", episode_event(D(2025, 6, 1)), [
    snap(0, "episode_status_asof", "Modified on appeal"), snap(0, "matter_status_asof", "Interim order"),
    snap(1, "episode_status_asof", None), snap(1, "matter_status_asof", "Interim order"),
])
scenario("N16_episode_event_for_episode_of_another_matter", "v31_scope", "An event scoped to an episode of another matter is invalid.",
         lambda d: d["LegalStatus"].append(dict(matter_id="M1", event_date=D(2025, 3, 1), public_date=D(2025, 3, 2),
                                                status="Modified on appeal", applies_to="Specific episode", episode_id="E2",
                                                source_order_id="O1")), [
    cellx("LegalStatus", 3, "check", "EPISODE MISSING OR WRONG"), decision(startswith="NOT VALID: fix the integrity checks"),
])


# ---- 7 settings: denominator policy
def v2_without_v1_evidence(d):
    add_correction(d)
    for _ in range(3):
        d["Evidence"].pop(0)              # remove the version-1 evidence rows (V01 to V03)


def v2_without_v1_latest(d):
    v2_without_v1_evidence(d)
    d["Rules"]["denom"] = "Latest version only"


scenario("N17a_denominator_latest_version_only", "v31_settings",
         "B18 set to Latest version only: version 1 needs no evidence once version 2 is audited.", v2_without_v1_latest, [
    cellx("Episodes", 0, "slots_expected_total", 5), cellx("Episodes", 0, "slots_valid_total", 5), gate("g_slots", "C", 1.0),
    decision(equals="PASS"),
])


def v2_without_v1_all(d):
    v2_without_v1_evidence(d)
    d["Rules"]["denom"] = "All versions"


scenario("N17b_denominator_all_versions", "v31_settings",
         "All versions: version 1 now needs its slots too (3 of 17 missing), so the share is 14/17 and the review is not complete.", v2_without_v1_all, [
    cellx("Episodes", 0, "slots_expected_total", 8), cellx("Episodes", 0, "slots_valid_total", 5), gate("g_slots", "C", 14 / 17),
    decision(startswith="IN PROGRESS (review not complete"),
])
# ---- 8 layout safety
scenario("N18_row_typed_below_the_formula_range", "v31_layout", "A matter typed in row 106, below the 100-row formula range, blocks the decision.",
         lambda d: d["Raw"].append(("Matters", "A106", "M99")), [
    gate("p_over", "C", 1), decision(startswith="NOT VALID: fix the integrity checks"),
])


# ================================================================== NEW IN v3.2
# ---- 1 decided defaults (the workbook is NOT given B18 / B19 here, so its own defaults apply)
def no_settings(d):
    del d["Rules"]["denom"]
    del d["Rules"]["indep"]


scenario("DEF1_workbook_defaults", "v32_defaults", "Untouched workbook: Rules B18 is All versions and B19 is Yes, and good data still passes.",
         no_settings, [cellref("Rules", "B18", "All versions"), cellref("Rules", "B19", "Yes"), decision(equals="PASS")])


def no_settings_not_independent(d):
    no_settings(d)
    d["People"][1]["independent"] = "No"


scenario("DEF2_default_requires_independent_auditor", "v32_defaults",
         "With the workbook's own B19 default, a non-independent auditor means no evidence counts.",
         no_settings_not_independent, [cellx("Evidence", 0, "valid", 0), gate("i_complete", "C", 0.0),
                                       decision(startswith="IN PROGRESS (review not complete: 0%")])


def no_settings_v2(d):
    no_settings(d)
    v2_without_v1_evidence(d)


scenario("DEF3_default_counts_every_version", "v32_defaults",
         "With the workbook's own B18 default, version 1 still needs its slots after version 2 exists.", no_settings_v2, [
    cellx("Episodes", 0, "slots_expected_total", 8), cellx("Episodes", 0, "slots_valid_total", 5), gate("g_slots", "C", 14 / 17),
    decision(startswith="IN PROGRESS (review not complete")])


# ---- 2 first disclosure needs a passage marked as disclosing the episode
def earlier_row(discloses, audit_result="Agree"):
    def f(d):
        d["Orders"].append(dict(order_id="O0", matter_id="M1", order_type="Show-cause notice (public)", order_date=D(2024, 1, 1),
                                public_date=D(2024, 1, 2), public_basis="Stated on SEBI website", total_pages=10))
        d["Evidence"].append(ev("V91", "M1", "E1", None, "instrument", "Alpha Ltd", "O0", discloses=discloses, audit_result=audit_result))
    return f


DELAY_EARLY = (D(2024, 1, 2) - D(2022, 7, 14)).days
scenario("N12b_identity_only_citation_blank_flag", "v32_disclosure",
         "A valid, audited identity row from an earlier order, flag left blank, does not set the first disclosure.",
         earlier_row(None), [cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Episodes", 0, "delay_days", 701),
                             cellx("Evidence", 14, "valid", 1), decision(equals="PASS")])
scenario("N12c_identity_only_citation_flag_no", "v32_disclosure",
         "The same row marked No does not set the first disclosure either.",
         earlier_row("No"), [cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Evidence", 14, "valid", 1)])
scenario("N12d_passage_marked_as_disclosing_counts", "v32_disclosure",
         "The same row marked Yes (the passage itself discloses the episode) sets the first disclosure to 2024-01-02.",
         earlier_row("Yes"), [cellx("Episodes", 0, "first_disclosure_date", "2024-01-02"), cellx("Episodes", 0, "disclosure_verified", "Yes"),
                              cellx("Episodes", 0, "delay_days", DELAY_EARLY), cellx("Episodes", 0, "latest_avail_date", "2024-06-14"),
                              decision(equals="PASS")])
scenario("N12e_marked_but_not_audited_is_ignored", "v32_disclosure",
         "A row marked Yes that was not audited is not valid, so it cannot set the first disclosure.",
         earlier_row("Yes", audit_result="Not audited"), [cellx("Evidence", 14, "valid", 0), cellx("Episodes", 0, "first_disclosure_date", "2024-06-14")])


def matter_level_marked(d):
    d["Evidence"].append(ev("V92", "M1", None, None, "legal_status", "Final order", "O1", discloses="Yes"))


scenario("N12f_matter_level_row_has_no_episode", "v32_disclosure",
         "A matter-level row (no episode ID) marked Yes does not set any episode's first disclosure.",
         matter_level_marked, [cellx("Episodes", 0, "first_disclosure_date", "2024-06-14"), cellx("Episodes", 1, "first_disclosure_date", "2023-03-02")])


# ---- 3 legal-event timing against the verified source date
scenario("L5_legal_public_one_day_before_source", "v32_legal",
         "An event public on 2024-06-13 cites an order made public (verified) on 2024-06-14: invalid, blocks the decision.",
         lambda d: d["LegalStatus"][0].update(event_date=D(2024, 6, 13), public_date=D(2024, 6, 13)), [
    cellx("LegalStatus", 0, "check", "PUBLIC BEFORE SOURCE"), gate("p_refs", "C", 1), decision(startswith="NOT VALID: fix the integrity checks")])
scenario("L6a_legal_public_same_day_as_source", "v32_legal", "Same day as the source order is allowed.",
         None, [cellx("LegalStatus", 0, "check", "OK"), decision(equals="PASS")])
scenario("L6b_legal_public_day_after_source", "v32_legal", "The day after the source order is allowed.",
         lambda d: d["LegalStatus"][0].update(event_date=D(2024, 6, 15), public_date=D(2024, 6, 15)),
         [cellx("LegalStatus", 0, "check", "OK"), decision(equals="PASS")])


def assumed_source(d):
    d["Orders"].append(dict(order_id="O4", matter_id="M1", order_type="Interim order", order_date=D(2024, 8, 1), public_date=D(2024, 8, 1),
                            public_basis="Same as order date (assumed)", total_pages=12))
    d["LegalStatus"].append(dict(matter_id="M1", event_date=D(2024, 7, 1), public_date=D(2024, 7, 1), status="Appeal filed",
                                 applies_to="Whole matter", source_order_id="O4"))


scenario("L7_source_date_only_assumed_kept_unverified", "v33_legal",
         "If the source order's public date is only assumed, the event is kept as SOURCE DATE UNVERIFIED. It does not block the decision.",
         assumed_source, [cellx("Orders", 3, "strict_ok", "No"), cellx("LegalStatus", 3, "check", "SOURCE DATE UNVERIFIED"),
                          gate("i_legal_unver", "C", 1), gate("p_refs", "C", 0), decision(equals="PASS")])


def assumed_source_snapshot(d):
    assumed_source(d)
    d["SnapshotDate"] = D(2024, 8, 5)


scenario("L7b_unverified_event_not_in_snapshot", "v33_legal",
         "The unverified appeal (public 2024-07-01, assumed source date 2024-08-01) is not shown in a snapshot of 2024-08-05; the last verified status is.",
         assumed_source_snapshot, [snap(0, "matter_status_asof", "Interim order")])


def only_unverified_event(d):
    d["Orders"].append(dict(order_id="O5", matter_id="M2", order_type="Interim order", order_date=D(2023, 3, 2), public_date=D(2023, 3, 2),
                            public_basis="Same as order date (assumed)", total_pages=5))
    d["LegalStatus"][2]["source_order_id"] = "O5"


scenario("L8_matter_with_only_unverified_event_not_documented", "v33_legal",
         "A matter whose only legal event is unverified does not count as documented; the normal gate shows it.",
         only_unverified_event, [cellx("LegalStatus", 2, "check", "SOURCE DATE UNVERIFIED"), cellx("Matters", 1, "status_documented", "No"),
                                 gate("g_legal", "C", 1), gate("i_legal_unver", "C", 1), gate("p_refs", "C", 0)])


# ---- 4 rows with data but no ID
def blank_id_order(d):
    d["Orders"].append(dict(order_id=None, matter_id="M1", order_type="Final order", order_date=D(2026, 4, 8), public_date=D(2026, 4, 10),
                            public_basis="Stated on SEBI website", total_pages=60))


NV = "NOT VALID: fix the integrity checks"
scenario("ID1_orders_blank_id", "v32_missing_ids", "An order with data but no order ID is flagged and blocks the decision.",
         blank_id_order, [cellx("Orders", 3, "order_check", "ID MISSING"), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID2_episodes_blank_id", "v32_missing_ids", "An episode with data but no episode ID is flagged and blocks the decision.",
         lambda d: d["Episodes"].append(dict(episode_id=None, matter_id="M1", instrument_name="Ghost Ltd", exchange="NSE", segment="Main board")),
         [cellx("Episodes", 2, "id_status", "ID MISSING"), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID3_matters_blank_id", "v32_missing_ids", "A matter with data but no matter ID is flagged and blocks the decision.",
         lambda d: d["Matters"].append(dict(matter_id=None, matter_name="Ghost matter", primary_scheme="Pump and dump")),
         [cellx("Matters", 2, "id_check", "ID MISSING"), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID4_versions_blank_id", "v32_missing_ids", "A label version with data but no version ID is flagged and blocks the decision.",
         lambda d: d["Versions"].append(dict(version_id=None, episode_id="E1", version_no=2, conduct_start=D(2021, 7, 14),
                                             conduct_end=D(2022, 9, 30), alleged_scheme="Pump and dump")),
         [cellx("Versions", 2, "id_status", "ID MISSING"), cellx("Episodes", 0, "n_versions", 1), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID5_legal_blank_matter_id", "v32_missing_ids", "A legal event with data but no matter ID is flagged and blocks the decision.",
         lambda d: d["LegalStatus"].append(dict(matter_id=None, event_date=D(2026, 4, 10), public_date=D(2026, 4, 10), status="Final order",
                                                applies_to="Whole matter", source_order_id="O2")),
         [cellx("LegalStatus", 3, "check", "ID MISSING"), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID6_evidence_blank_id", "v32_missing_ids", "An evidence row with data but no evidence ID is flagged and blocks the decision.",
         lambda d: d["Evidence"].append(ev(None, "M1", "E1", None, "isin", "INE111A01011", "O1")),
         [cellx("Evidence", 14, "id_status", "ID MISSING"), cellx("Evidence", 14, "valid", None), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID7_people_blank_name", "v32_missing_ids", "A person row with a role but no name is flagged and blocks the decision.",
         lambda d: d["People"].append(dict(name=None, role="Reviewer", independent="Yes")),
         [cellx("People", 2, "id_check", "ID MISSING"), gate("p_refs", "C", 1), decision(startswith=NV)])
scenario("ID8_selectionlog_blank_id", "v32_missing_ids", "A selection-log row with a candidate but no log ID blocks the decision.",
         lambda d: d["Raw"].append(("SelectionLog", "C30", "Candidate typed without a log ID")),
         [gate("p_log", "C", 1), decision(startswith=NV)])


def blank_links(d):
    d["Orders"][0]["matter_id"] = None
    d["Episodes"][0]["matter_id"] = None
    d["Versions"][0]["episode_id"] = None


scenario("ID9_blank_links_read_as_unknown", "v32_missing_ids", "A blank matter or episode link is UNKNOWN, never silently accepted.",
         blank_links, [cellx("Orders", 0, "order_check", "UNKNOWN MATTER"), cellx("Episodes", 0, "id_status", "UNKNOWN MATTER"),
                       cellx("Versions", 0, "id_status", "UNKNOWN EPISODE"), decision(startswith=NV)])


# ---- 5 CONDITIONAL never overrides an integrity or leakage failure
def conditional_level(d):
    d["Episodes"][1]["mkt_warmup"] = "Partial"          # 1 strict episode: CONDITIONAL on its own (see W1)


def cx(extra):
    def f(d):
        conditional_level(d)
        extra(d)
    return f


scenario("CX0_control_conditional", "v32_conditional", "Control: this data alone gives CONDITIONAL.", conditional_level, [decision(equals="CONDITIONAL")])
scenario("CX1_leak_test_failing", "v32_conditional", "Conditional-level data with a failing leak test is NOT VALID, not CONDITIONAL.",
         cx(lambda d: d["Gates"].update(g_leak="Failing")), [decision(startswith=NV)])
scenario("CX2_duplicate_id", "v32_conditional", "Conditional-level data with a duplicate order ID is NOT VALID.",
         cx(lambda d: d["Orders"].append(deepcopy(d["Orders"][0]))), [decision(startswith=NV)])
scenario("CX3_missing_id", "v32_conditional", "Conditional-level data with a row that has no ID is NOT VALID.", cx(blank_id_order), [decision(startswith=NV)])
scenario("CX4_legal_before_source", "v32_conditional", "Conditional-level data with a legal event before its source is NOT VALID.",
         cx(lambda d: d["LegalStatus"][0].update(event_date=D(2024, 6, 13), public_date=D(2024, 6, 13))), [decision(startswith=NV)])
scenario("CX5_leak_test_not_run", "v32_conditional",
         "Documented behaviour: a leak test that has not been run is not a failure, so CONDITIONAL is still shown. Only Failing blocks.",
         cx(lambda d: d["Gates"].update(g_leak="Not run")), [decision(equals="CONDITIONAL")])

# ---- 6 the lag is a calendar-day lag (stated, not a trading calendar)
FRI, SAT, MON = D(2024, 6, 14), D(2024, 6, 15), D(2024, 6, 17)
scenario("C3a_public_friday_snapshot_friday", "v32_lag", "Public on Friday 2024-06-14: on the same Friday it is not usable (lag 1).",
         snapdate(FRI), [snap(0, "label_available", "No")])
scenario("C3b_public_friday_snapshot_monday", "v32_lag",
         "Public on Friday: the next session is Monday 2024-06-17 and the label is usable then. Calendar lag and next-session rule agree on a session date.",
         snapdate(MON), [snap(0, "label_available", "Yes"), snap(0, "version_asof", 1)])
scenario("C3c_public_friday_snapshot_saturday", "v32_lag",
         "Documented limit: on Saturday (not a trading session) the calendar-day lag already shows the label. Use trading sessions as snapshot dates.",
         snapdate(SAT), [snap(0, "label_available", "Yes")])


# ================================================================== NEW IN v3.3
# ---- delay statistics use verified first disclosure only
scenario("DX0_delay_statistics_all_verified", "v33_delay", "Both first-disclosure dates verified: two delays, nothing left out.",
         None, [gate("d_count", "B", 2), gate("d_excl", "B", 0), gate("d_median", "B", 533.5), gate("i_legal_unver", "C", 0)])


def e1_without_disclosing_row(d):
    for e in d["Evidence"]:
        if e["episode_id"] == "E1":
            e["discloses"] = None


scenario("DX2_no_disclosing_row_left_out", "v33_delay", "E1 has no row marked as disclosing it: no first disclosure, no delay, counted as left out.",
         e1_without_disclosing_row, [cellx("Episodes", 0, "first_disclosure_date", None), cellx("Episodes", 0, "delay_days", None),
                                     gate("d_count", "B", 1), gate("d_excl", "B", 1), gate("d_median", "B", 366)])

# ---- selection log reconciled with Matters
def sel_edit(extra=(), keep=None):
    def f(d):
        rows = default_sellog(d)
        if keep is not None:
            rows = [r for r in rows if r["matter_id"] in keep]
        d["SelLog"] = rows + list(extra)
    return f


scenario("SEL1_included_matter_not_in_registry", "v33_selection", "An Included row whose matter is not in Matters blocks the decision.",
         sel_edit([dict(log_id="L3", decision="Included", matter_id="M9")]),
         [cellx("SelectionLog", 2, "log_check", "MATTER NOT IN REGISTRY"), gate("p_log", "C", 1), decision(startswith=NV)])
scenario("SEL2_log_id_without_decision", "v33_selection", "A log ID with no decision blocks the decision.",
         sel_edit([dict(log_id="L3", decision=None)]),
         [cellx("SelectionLog", 2, "log_check", "DECISION MISSING"), gate("p_log", "C", 1), decision(startswith=NV)])
scenario("SEL3_matter_without_log_entry", "v33_selection", "An in-scope matter with no Included log row blocks the decision.",
         sel_edit(keep=["M1"]),
         [cellx("Matters", 1, "sel_entry", "NO LOG ENTRY"), cellx("Matters", 0, "sel_entry", "OK"), gate("p_log", "C", 1), decision(startswith=NV)])


def documented_exclusions(d):
    d["Matters"].append(dict(matter_id="M3", matter_name="Excluded matter", primary_scheme="Pump and dump", time_stratum="2021-2025",
                             review_status="Excluded after review"))
    sel_edit([dict(log_id="L3", decision="Excluded", exclusion_reason="Not a market-abuse matter")], keep=["M1", "M2"])(d)


scenario("SEL4_documented_exclusions_raise_no_error", "v33_selection",
         "An Excluded log row with a reason, and a matter excluded after review with no Included row, are documented exclusions: no error.",
         documented_exclusions, [cellx("SelectionLog", 2, "log_check", "OK"), cellx("Matters", 2, "sel_entry", "Excluded after review"),
                                 gate("p_log", "C", 0), decision(equals="PASS")])


def draft_with_errors(d):
    d["Rules"]["freeze"] = None
    sel_edit(keep=["M1"])(d)


scenario("SEL5_draft_shown_first_errors_visible", "v33_selection",
         "While the protocol is not frozen, DRAFT is the decision text and the selection-log error is still counted on Gates.",
         draft_with_errors, [gate("p_log", "C", 1), cellx("Matters", 1, "sel_entry", "NO LOG ENTRY"), decision(startswith="DRAFT")])


def jsonable():
    """Scenario list for expected_outputs.json (data omitted)."""
    return [dict(name=s["name"], group=s["group"], description=s["desc"], expect=s["expect"]) for s in S]
