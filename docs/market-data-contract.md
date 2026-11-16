# Market Data Contract & Ingestion Specification

**Evidrava Point-in-Time Market Evidence Benchmark**

This document specifies the technical requirements, column schemas, integrity constraints, and warm-up rules for daily cash-equity market data used in the Evidrava benchmark.

---

## 1. Scope & Primary Venue

Evidrava benchmarks trading anomaly detectors on Indian cash-equity secondary market orders issued by SEBI.
- **Primary venues**: National Stock Exchange of India (NSE) and BSE Limited (BSE).
- **Temporal frequency**: Daily end-of-day (EOD) summary bars (Bhavcopy). Intraday tick data is explicitly deferred.
- **Date convention**: All dates are strictly ISO 8601 calendar dates (`YYYY-MM-DD`) referencing the `Asia/Kolkata` trading day.

---

## 2. Daily Bar Schema (`market_data.csv`)

A valid market data file must be a UTF-8 encoded CSV file adhering to the following structure:

| Column | Type | Nullable | Description & Constraints |
|---|---|---|---|
| `date` | String (`YYYY-MM-DD`) | No | Trading date. Must match an official trading session in the venue calendar. |
| `isin` | String (`[A-Z]{2}[A-Z0-9]{9}[0-9]`) | No | Exact 12-character International Securities Identification Number (e.g. `INE002A01018`). |
| `symbol` | String | No | Official exchange trading ticker / series symbol during the active trading interval. |
| `open` | Float (> 0) | No | Official session opening price in INR. Must satisfy `low <= open <= high`. |
| `high` | Float (> 0) | No | Official session peak price in INR. Must satisfy `high >= low`. |
| `low` | Float (> 0) | No | Official session trough price in INR. Must satisfy `low <= high`. |
| `close` | Float (> 0) | No | Official session closing / settlement price in INR. Must satisfy `low <= close <= high`. |
| `volume` | Integer (>= 0) | No | Total traded quantity (shares) during the session. |
| `unadjusted_close` | Float (> 0) | Yes | Raw closing price before split/bonus/dividend adjustments (optional). |
| `value` | Float (>= 0) | Yes | Gross turnover value in INR (optional). |
| `trades` | Integer (>= 0) | Yes | Total trade count executed during the session (optional). |

---

## 3. Strict Integrity Constraints

1. **Numeric Bound Consistency**:
   - `high >= low`
   - `low <= open <= high`
   - `low <= close <= high`
   - `open > 0`, `high > 0`, `low > 0`, `close > 0`
   - `volume >= 0`
2. **Chronological Uniqueness**:
   - The pair `(isin, date)` must be unique. No duplicate records are allowed.
   - For any single `isin`, records must appear in strictly ascending chronological order: `date[i] < date[i+1]`.
3. **Session Calendar Consistency**:
   - If a venue calendar is provided, every `date` in the market series must correspond to an active trading day (`session_type == 'regular'`). Non-session or weekend dates are rejected.
4. **Warm-Up Lookback Constraint**:
   - Trading anomaly detectors require feature stabilization before evaluating an alleged conduct window.
   - The recommended minimum warm-up window is **252 trading sessions** (~1 calendar year) immediately preceding the alleged conduct start date.
   - An episode whose historical prices cover fewer than 252 trading sessions before conduct start receives a diagnostic warning (`INSUFFICIENT_WARM_UP`) and cannot qualify as a `strict` episode.

---

## 4. Verification Command

Validate any market data CSV using the built-in Evidrava tool:

```powershell
python -m evidrava check-market-data --data path/to/prices.csv --out runs/market-check-01
```

Optional parameters:
- `--sessions path/to/sessions.csv`: Enforces venue trading calendar alignment.
- `--warm-up-bars 252`: Verifies minimum lookback bars per instrument.

The command outputs `market_data.json`, `report.html`, and a checksum `manifest.json`. The research decision remains `NOT_EVALUATED`.
