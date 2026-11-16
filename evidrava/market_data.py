"""Market data schema validation and trading session coverage checker."""
import csv
from collections import Counter
from datetime import date
from hashlib import sha256
from pathlib import Path
import re

MARKET_FIELDS = ["date", "isin", "symbol", "open", "high", "low", "close", "volume"]
OPTIONAL_FIELDS = ["unadjusted_close", "value", "trades"]
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _diagnostic(code, row, field, message, severity="error"):
    return {
        "code": code,
        "row": row,
        "field": field,
        "message": message,
        "severity": severity,
    }


def inspect_market_data(path, session_dates=None, min_warm_up_bars=0):
    """Validate daily cash-equity market bars against the Evidrava market data contract."""
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Market data file not found: {path}")

    blob = path.read_bytes()
    file_sha256 = sha256(blob).hexdigest()

    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Market data CSV must be valid UTF-8 text") from exc

    stream = text.splitlines()
    if not stream:
        raise ValueError("Market data CSV is empty")

    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise ValueError("Market data CSV has no header row")

    missing_fields = [f for f in MARKET_FIELDS if f not in reader.fieldnames]
    if missing_fields:
        raise ValueError("Market data CSV missing required columns: " + ", ".join(missing_fields))

    diagnostics = []
    seen_keys = set()
    isin_dates = {}
    valid_rows = 0
    unique_isins = set()
    unique_symbols = set()
    all_dates = []

    for row_idx, row in enumerate(reader, start=2):
        d_str = (row.get("date") or "").strip()
        isin = (row.get("isin") or "").strip()
        symbol = (row.get("symbol") or "").strip()

        # Check date
        if not d_str or not DATE_PATTERN.fullmatch(d_str):
            diagnostics.append(_diagnostic("INVALID_DATE_FORMAT", row_idx, "date", f"Invalid date: {d_str!r}"))
            continue
        try:
            row_date = date.fromisoformat(d_str)
        except ValueError:
            diagnostics.append(_diagnostic("INVALID_DATE_VALUE", row_idx, "date", f"Nonexistent calendar date: {d_str}"))
            continue

        # Check session calendar
        if session_dates is not None and row_date not in session_dates:
            diagnostics.append(_diagnostic("NON_SESSION_DATE", row_idx, "date", f"Date {d_str} is not a valid trading session in the calendar"))

        # Check ISIN
        if not isin or not ISIN_PATTERN.fullmatch(isin):
            diagnostics.append(_diagnostic("INVALID_ISIN", row_idx, "isin", f"Invalid 12-character ISIN: {isin!r}"))
            continue

        if not symbol:
            diagnostics.append(_diagnostic("MISSING_SYMBOL", row_idx, "symbol", "Trading symbol cannot be empty"))

        # Check duplicate (isin, date)
        key = (isin, row_date)
        if key in seen_keys:
            diagnostics.append(_diagnostic("DUPLICATE_RECORD", row_idx, "date", f"Duplicate bar for ISIN {isin} on {d_str}"))
            continue
        seen_keys.add(key)

        # Check price fields
        try:
            p_open = float(row.get("open", ""))
            p_high = float(row.get("high", ""))
            p_low = float(row.get("low", ""))
            p_close = float(row.get("close", ""))
        except (ValueError, TypeError):
            diagnostics.append(_diagnostic("INVALID_PRICE_FORMAT", row_idx, "open/high/low/close", "Prices must be numerical"))
            continue

        if p_open <= 0 or p_high <= 0 or p_low <= 0 or p_close <= 0:
            diagnostics.append(_diagnostic("NON_POSITIVE_PRICE", row_idx, "open/high/low/close", "Prices must be strictly positive"))
            continue

        if p_low > p_high:
            diagnostics.append(_diagnostic("LOW_EXCEEDS_HIGH", row_idx, "low", f"Low ({p_low}) exceeds High ({p_high})"))
        if not (p_low <= p_open <= p_high):
            diagnostics.append(_diagnostic("OPEN_OUT_OF_BOUNDS", row_idx, "open", f"Open ({p_open}) outside [Low {p_low}, High {p_high}]"))
        if not (p_low <= p_close <= p_high):
            diagnostics.append(_diagnostic("CLOSE_OUT_OF_BOUNDS", row_idx, "close", f"Close ({p_close}) outside [Low {p_low}, High {p_high}]"))

        # Check volume
        v_str = (row.get("volume") or "").strip()
        try:
            vol = int(v_str)
            if vol < 0:
                diagnostics.append(_diagnostic("NEGATIVE_VOLUME", row_idx, "volume", f"Volume cannot be negative: {vol}"))
        except ValueError:
            diagnostics.append(_diagnostic("INVALID_VOLUME", row_idx, "volume", f"Volume must be an integer: {v_str!r}"))

        # Check chronology per ISIN
        if isin in isin_dates:
            last_date = isin_dates[isin]
            if row_date <= last_date:
                diagnostics.append(_diagnostic("CHRONOLOGY_VIOLATION", row_idx, "date", f"Date {d_str} is not strictly after preceding date {last_date.isoformat()} for ISIN {isin}"))
        isin_dates[isin] = row_date

        valid_rows += 1
        unique_isins.add(isin)
        unique_symbols.add(symbol)
        all_dates.append(row_date)

    # Check warm-up requirement
    if min_warm_up_bars > 0:
        for isin, bar_count in Counter(k[0] for k in seen_keys).items():
            if bar_count < min_warm_up_bars:
                diagnostics.append(_diagnostic("INSUFFICIENT_WARM_UP", None, "volume",
                                               f"ISIN {isin} has only {bar_count} bars; minimum {min_warm_up_bars} required for warm-up",
                                               severity="warning"))

    status = "INVALID" if any(d["severity"] == "error" for d in diagnostics) else "VALID"

    date_range = None
    if all_dates:
        date_range = {
            "start": min(all_dates).isoformat(),
            "end": max(all_dates).isoformat(),
            "total_trading_days": len(set(all_dates)),
        }

    return {
        "report_kind": "market-data-check",
        "status": status,
        "research_decision": "NOT_EVALUATED",
        "file_name": path.name,
        "file_sha256": file_sha256,
        "summary": {
            "total_rows": valid_rows,
            "unique_isins": len(unique_isins),
            "unique_symbols": len(unique_symbols),
            "date_range": date_range,
            "error_count": sum(d["severity"] == "error" for d in diagnostics),
            "warning_count": sum(d["severity"] == "warning" for d in diagnostics),
        },
        "unique_isins": sorted(unique_isins),
        "unique_symbols": sorted(unique_symbols),
        "diagnostics": diagnostics,
        "limitations": [
            "This check confirms schema, numeric consistency, and chronological order; it does not verify source exchange provenance.",
            "Adjustments for splits, rights, and bonus issues must be documented via corporate action manifests.",
            "Valid market data does not confer detector validity or alter the NOT_EVALUATED research decision.",
        ],
    }
