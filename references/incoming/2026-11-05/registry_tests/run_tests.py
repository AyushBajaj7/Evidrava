#!/usr/bin/env python3
"""Run the executable fixtures against SEBI_Episode_Registry_v3.xlsx.

Requires: Python 3.9+, openpyxl, and LibreOffice (to recalculate the formulas).
Usage examples:
    python run_tests.py --workbook ../SEBI_Episode_Registry_v3.xlsx
    python run_tests.py --only D1 --only snapshot
    SOFFICE="C:/Program Files/LibreOffice/program/soffice.exe" python run_tests.py
Exit code 0 = all expectations met.
"""
import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fixtures  # noqa: E402

MAPS = json.load(open(HERE / "maps.json"))
L, SL, G, R0 = MAPS["L"], MAPS["SL"], MAPS["G"], MAPS["R0"]
TABLES = ["Matters", "Orders", "Episodes", "Versions", "LegalStatus", "Evidence"]


# ----------------------------------------------------------------- building scenario workbooks
def apply_data(wb, data):
    for k, v in data["Rules"].items():
        wb["Rules"][MAPS["RULE"][k]] = v
    for i, v in enumerate(data["Strata"]):
        wb["Rules"][f"B{MAPS['STRATA_ROWS'][0] + i}"] = v
    for k, v in data["Gates"].items():
        wb["Gates"][f"C{G[k]}"] = v
    if data["SnapshotDate"] is not None:
        wb["Snapshot"]["B3"] = data["SnapshotDate"]
    for sheet in TABLES:
        for i, row in enumerate(data[sheet]):
            r = R0 + i
            for key, val in row.items():
                wb[sheet][f"{L[sheet][key]}{r}"] = val


def build_one(args):
    template, name, data, outdir = args
    wb = load_workbook(template)
    apply_data(wb, data)
    path = os.path.join(outdir, f"{name}.xlsx")
    wb.save(path)
    return name


# ----------------------------------------------------------------- reading results
def norm(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    if v == "":
        return None
    if isinstance(v, float) and abs(v - round(v)) < 1e-9 and abs(v) < 1e12:
        return int(round(v))
    return v


def same(actual, expected, tol=1e-6):
    a, e = norm(actual), norm(expected)
    if isinstance(a, (int, float)) and isinstance(e, (int, float)) and not isinstance(a, bool):
        return abs(a - e) <= tol
    return a == e


def snapshot_rows(wb):
    ws = wb["Snapshot"]
    rows = []
    for r in range(R0, MAPS["LAST"]["Snapshot"] + 1):
        vals = [norm(ws[f"{SL[k]}{r}"].value) for k in SL]
        if vals[0] is None:
            continue
        rows.append(vals)
    return rows


def evaluate(name, wb, expects, cache):
    problems = []
    for ex in expects:
        t = ex["type"]
        try:
            if t == "decision":
                act = wb["Gates"]["B4"].value
                ok = (str(act).startswith(ex["startswith"]) if ex.get("startswith") else same(act, ex["equals"]))
                what = f"decision expected {ex.get('equals') or ex.get('startswith')!r}"
            elif t == "gate":
                act = wb["Gates"][f"{ex['col']}{G[ex['name']]}"].value
                ok, what = same(act, ex["equals"], ex.get("tol", 1e-6)), f"Gates {ex['name']} col {ex['col']} expected {ex['equals']!r}"
            elif t == "cell":
                act = wb[ex["sheet"]][f"{L[ex['sheet']][ex['key']]}{R0 + ex['row']}"].value
                ok, what = same(act, ex["equals"]), f"{ex['sheet']} row {ex['row']} {ex['key']} expected {ex['equals']!r}"
            elif t == "snapshot":
                act = wb["Snapshot"][f"{SL[ex['key']]}{R0 + ex['row']}"].value
                ok, what = same(act, ex["equals"]), f"Snapshot row {ex['row']} {ex['key']} expected {ex['equals']!r}"
            elif t == "snapshot_count":
                act = wb["Snapshot"]["B4"].value
                ok, what = same(act, ex["equals"]), f"Snapshot episodes with a label expected {ex['equals']!r}"
            elif t == "maturity":
                act = wb["Gates"][f"{ex['col']}{MAPS['MAT_ROWS'][ex['key']]}"].value
                ok, what = same(act, ex["equals"]), f"maturity {ex['key']} col {ex['col']} expected {ex['equals']!r}"
            elif t == "stratum":
                act = wb["Gates"][f"{ex['col']}{G['strat_1'] + ex['row']}"].value
                ok, what = same(act, ex["equals"]), f"stratum row {ex['row']} col {ex['col']} expected {ex['equals']!r}"
            elif t == "snapshot_same_as":
                other = cache.get(ex["scenario"])
                act = snapshot_rows(wb)
                ok = other is not None and act == other
                what = f"snapshot identical to scenario {ex['scenario']}" + ("" if other is not None else " (reference not run)")
                act = "identical" if ok else f"differs ({len(act)} rows vs {len(other) if other else 'n/a'})"
            else:
                ok, what, act = False, f"unknown expectation {t}", None
        except Exception as exc:  # noqa
            ok, what, act = False, f"{t} could not be evaluated: {exc}", None
        if not ok:
            problems.append(f"{what}; got {norm(act)!r}")
    errors = [f"{ws.title}!{c.coordinate}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
              if isinstance(c.value, str) and c.value.startswith("#")]
    if errors:
        problems.append(f"formula error cells: {errors[:5]}")
    return problems


def read_out(args):
    path, name, expects = args
    wb = load_workbook(path, data_only=True)
    return name, wb["Gates"]["B4"].value, snapshot_rows(wb), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", default=str(HERE.parent / "SEBI_Episode_Registry_v3.xlsx"))
    ap.add_argument("--soffice", default=os.environ.get("SOFFICE", "soffice"))
    ap.add_argument("--only", action="append", default=[], help="substring of scenario name or group (repeatable)")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--workdir", default=str(HERE / "_work"))
    ap.add_argument("--dump-expected", action="store_true", help="write expected_outputs.json and exit")
    args = ap.parse_args()

    if args.dump_expected:
        json.dump(fixtures.jsonable(), open(HERE / "expected_outputs.json", "w"), indent=1)
        print("wrote expected_outputs.json with", len(fixtures.S), "scenarios")
        return 0

    chosen = [s for s in fixtures.S if not args.only or any(o.lower() in (s["name"] + " " + s["group"]).lower() for o in args.only)]
    # a snapshot-comparison scenario needs its reference scenario
    names = {s["name"] for s in chosen}
    for s in list(chosen):
        for ex in s["expect"]:
            if ex["type"] == "snapshot_same_as" and ex["scenario"] not in names:
                chosen.insert(0, next(x for x in fixtures.S if x["name"] == ex["scenario"]))
                names.add(ex["scenario"])
    work = Path(args.workdir)
    if work.exists():
        shutil.rmtree(work)
    (work / "in").mkdir(parents=True)
    (work / "out").mkdir()

    print(f"Building {len(chosen)} scenario workbooks from {args.workbook} ...")
    jobs = [(args.workbook, s["name"], s["data"], str(work / "in")) for s in chosen]
    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            list(ex.map(build_one, jobs))
    else:
        for j in jobs:
            build_one(j)

    print("Recalculating with LibreOffice (one process for all files) ...")
    cmd = shlex.split(args.soffice, posix=(os.name != "nt")) + ["--headless", "--convert-to", "xlsx", "--outdir", str(work / "out")]
    cmd += [str(work / "in" / f"{s['name']}.xlsx") for s in chosen]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
        return 2

    cache, failures, rows = {}, 0, []
    outs = {}
    for s in chosen:                                   # reference scenarios first (list order)
        wb = load_workbook(work / "out" / f"{s['name']}.xlsx", data_only=True)
        outs[s["name"]] = wb
        cache[s["name"]] = snapshot_rows(wb)
    for s in chosen:
        problems = evaluate(s["name"], outs[s["name"]], s["expect"], cache)
        status = "PASS" if not problems else "FAIL"
        failures += bool(problems)
        rows.append((status, s["name"], s["desc"], problems, outs[s["name"]]["Gates"]["B4"].value))
    width = max(len(r[1]) for r in rows)
    for status, name, desc, problems, dec in rows:
        print(f"[{status}] {name:<{width}}  decision: {dec}")
        for p in problems:
            print(f"        - {p}")
    print(f"\n{len(rows) - failures} of {len(rows)} scenarios passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
