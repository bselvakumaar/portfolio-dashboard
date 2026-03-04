import logging
import time
from typing import Any

import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import AverageTrueRange

logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    pass


def fetch_ohlc_data(
    ticker: str,
    period: str,
    interval: str,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> pd.DataFrame:
    """Fetch OHLCV data for one ticker with retry and backoff."""
    for attempt in range(1, retry_attempts + 1):
        try:
            logger.info(
                "Fetching OHLC data",
                extra={
                    "ticker": ticker,
                    "period": period,
                    "interval": interval,
                    "attempt": attempt,
                },
            )
            history = yf.Ticker(ticker).history(period=period, interval=interval)
            if history.empty:
                raise DataFetchError(f"No data returned for {ticker}")
            return history
        except Exception as exc:
            logger.warning(
                "Failed to fetch OHLC data",
                exc_info=True,
                extra={"ticker": ticker, "attempt": attempt},
            )
            if attempt == retry_attempts:
                raise DataFetchError(f"Failed to fetch data for {ticker}") from exc
            time.sleep(retry_backoff_seconds * attempt)
    raise DataFetchError(f"Exhausted retries for {ticker}")


def calculate_indicators(df: pd.DataFrame) -> dict[str, Any]:
    """Compute quant indicators from OHLCV dataframe and return the latest values."""
    required_cols = {"Open", "High", "Low", "Close", "Volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = df.copy().dropna()
    if data.empty:
        raise ValueError("Empty dataframe after dropping NA values")

    close = data["Close"]
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]

    data["rsi_14"] = RSIIndicator(close=close, window=14).rsi()
    data["sma_20"] = SMAIndicator(close=close, window=20).sma_indicator()
    data["sma_50"] = SMAIndicator(close=close, window=50).sma_indicator()
    data["macd"] = MACD(close=close).macd_diff()
    data["atr_14"] = AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
    data["rolling_52w_high"] = close.rolling(window=252, min_periods=20).max()
    data["high_proximity_pct"] = (close / data["rolling_52w_high"]) * 100.0
    data["avg_volume_20"] = volume.rolling(window=20, min_periods=1).mean()
    data["volume_spike_ratio"] = volume / data["avg_volume_20"]

    latest = data.iloc[-1]
    return {
        "close": float(latest["Close"]),
        "rsi_14": float(latest["rsi_14"]),
        "sma_20": float(latest["sma_20"]),
        "sma_50": float(latest["sma_50"]),
        "macd": float(latest["macd"]),
        "atr_14": float(latest["atr_14"]),
        "high_proximity_pct": float(latest["high_proximity_pct"]),
        "volume_spike_ratio": float(latest["volume_spike_ratio"]),
    }
