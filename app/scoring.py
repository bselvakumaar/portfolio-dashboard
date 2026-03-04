from typing import Any


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rsi_norm(rsi: float) -> float:
    # Prefers mid-high RSI regime without rewarding extreme overbought values.
    return _clamp(1.0 - abs(rsi - 60.0) / 40.0, 0.0, 1.0)


def _volatility_norm(atr_pct: float) -> float:
    # Reward lower ATR% (stable trends): <=2 excellent, >=8 weak.
    return _clamp((8.0 - atr_pct) / 6.0, 0.0, 1.0)


def compute_steward_score(
    indicators: dict[str, Any],
    sentiment_score: float,
    weights: dict[str, float],
) -> dict[str, Any]:
    close = float(indicators["close"])
    rsi = float(indicators["rsi_14"])
    sma_20 = float(indicators["sma_20"])
    sma_50 = float(indicators["sma_50"])
    macd = float(indicators["macd"])
    atr = float(indicators["atr_14"])
    high_proximity = float(indicators["high_proximity_pct"])
    volume_spike = float(indicators["volume_spike_ratio"])

    macd_norm = 1.0 if macd > 0 else 0.0
    high_prox_norm = _clamp((high_proximity - 85.0) / 15.0, 0.0, 1.0)
    momentum_norm = (0.5 * macd_norm) + (0.5 * high_prox_norm)

    price_above_sma20 = 1.0 if close > sma_20 else 0.0
    sma20_above_sma50 = 1.0 if sma_20 > sma_50 else 0.0
    trend_norm = (0.6 * price_above_sma20) + (0.4 * sma20_above_sma50)

    volume_norm = _clamp((volume_spike - 1.0) / 2.0, 0.0, 1.0)
    rsi_strength_norm = _rsi_norm(rsi)
    atr_pct = (atr / close) * 100.0 if close > 0 else 100.0
    volatility_norm = _volatility_norm(atr_pct)
    sentiment_norm = _clamp(sentiment_score / 10.0, 0.0, 1.0)

    components = {
        "momentum": momentum_norm * weights["momentum"],
        "trend_strength": trend_norm * weights["trend_strength"],
        "volume_strength": volume_norm * weights["volume_strength"],
        "rsi_strength": rsi_strength_norm * weights["rsi_strength"],
        "volatility_control": volatility_norm * weights["volatility_control"],
        "ai_sentiment": sentiment_norm * weights["ai_sentiment"],
    }

    final_score = round(_clamp(sum(components.values()), 0.0, 100.0), 2)
    rounded_components = {k: round(v, 2) for k, v in components.items()}
    return {
        "components": rounded_components,
        "final_score": final_score,
        "diagnostics": {
            "atr_pct": round(atr_pct, 2),
            "high_proximity_pct": round(high_proximity, 2),
            "volume_spike_ratio": round(volume_spike, 2),
        },
    }
