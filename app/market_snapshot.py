from datetime import datetime, timezone
from typing import Any

from app.indicators import fetch_ohlc_data

SECTOR_MAP: dict[str, str] = {
    "RELIANCE.NS": "Energy",
    "TCS.NS": "IT",
    "HDFCBANK.NS": "Banking",
    "INFY.NS": "IT",
    "ICICIBANK.NS": "Banking",
    "ITC.NS": "FMCG",
    "LT.NS": "Infrastructure",
    "SBIN.NS": "Banking",
    "AXISBANK.NS": "Banking",
    "KOTAKBANK.NS": "Banking",
    "BHARTIARTL.NS": "Telecom",
    "HINDUNILVR.NS": "FMCG",
    "BAJFINANCE.NS": "NBFC",
    "MARUTI.NS": "Auto",
    "TITAN.NS": "Consumer",
    "ASIANPAINT.NS": "Materials",
    "WIPRO.NS": "IT",
    "HCLTECH.NS": "IT",
    "SUNPHARMA.NS": "Pharma",
    "NTPC.NS": "Utilities",
}


def _row_for_ticker(
    ticker: str,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, Any] | None:
    try:
        df = fetch_ohlc_data(
            ticker=ticker,
            period="10d",
            interval="1d",
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        if len(df) < 2:
            return None
        latest_close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        latest_volume = float(df["Volume"].iloc[-1])
        day_return_pct = ((latest_close - prev_close) / prev_close) * 100.0 if prev_close else 0.0
        return {
            "ticker": ticker,
            "sector": SECTOR_MAP.get(ticker, "Unknown"),
            "close": round(latest_close, 2),
            "prev_close": round(prev_close, 2),
            "day_return_pct": round(day_return_pct, 2),
            "volume": int(latest_volume),
        }
    except Exception:
        return None


def build_market_snapshot(
    tickers: list[str],
    top_n: int,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        row = _row_for_ticker(
            ticker=ticker,
            retry_attempts=retry_attempts,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        if row:
            rows.append(row)

    ranked = sorted(rows, key=lambda x: float(x["day_return_pct"]), reverse=True)
    top_gainers = ranked[:top_n]
    top_losers = list(reversed(ranked[-top_n:]))

    sector_acc: dict[str, dict[str, float]] = {}
    for row in rows:
        sec = row["sector"]
        sector_acc.setdefault(sec, {"sum_return": 0.0, "count": 0, "sum_volume": 0.0})
        sector_acc[sec]["sum_return"] += float(row["day_return_pct"])
        sector_acc[sec]["count"] += 1
        sector_acc[sec]["sum_volume"] += float(row["volume"])

    sector_summary = []
    for sector, agg in sector_acc.items():
        avg_ret = agg["sum_return"] / agg["count"] if agg["count"] else 0.0
        sector_summary.append(
            {
                "sector": sector,
                "scripts": int(agg["count"]),
                "avg_day_return_pct": round(avg_ret, 2),
                "total_volume": int(agg["sum_volume"]),
            }
        )
    sector_summary.sort(key=lambda x: float(x["avg_day_return_pct"]), reverse=True)

    return {
        "as_of_utc": datetime.now(tz=timezone.utc).isoformat(),
        "coverage_count": len(rows),
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "sector_summary": sector_summary,
    }
