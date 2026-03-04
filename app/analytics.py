from typing import Any


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def enrich_with_predictions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach prediction metrics and recommendation labels to successful ticker results."""
    enriched: list[dict[str, Any]] = []
    for row in results:
        if row.get("status") != "ok":
            enriched.append(row)
            continue

        indicators = row.get("indicators", {})
        diagnostics = row.get("diagnostics", {})
        close = float(indicators.get("close", 0.0))
        macd = float(indicators.get("macd", 0.0))
        volume_spike = float(indicators.get("volume_spike_ratio", 1.0))
        atr_pct = float(diagnostics.get("atr_pct", 100.0))
        sentiment = float(row.get("sentiment_score_raw", 0.0))
        score = float(row.get("final_score", 0.0))

        momentum_factor = _clamp((macd / max(close, 1e-9)) * 100.0, -3.0, 3.0)
        score_factor = (score - 50.0) / 10.0
        sentiment_factor = (sentiment - 5.0) * 0.4
        volume_factor = _clamp((volume_spike - 1.0) * 2.5, -2.0, 4.0)
        volatility_drag = _clamp(atr_pct * 0.45, 0.0, 8.0)

        predicted_21d_return_pct = round(
            _clamp(
                score_factor + sentiment_factor + momentum_factor + volume_factor - volatility_drag,
                -15.0,
                20.0,
            ),
            2,
        )
        base_daily_return = predicted_21d_return_pct / 21.0
        predicted_3d_return_pct = round(base_daily_return * 3.0, 2)
        predicted_5d_return_pct = round(base_daily_return * 5.0, 2)
        predicted_7d_return_pct = round(base_daily_return * 7.0, 2)
        downside_risk_21d_pct = round(_clamp(atr_pct * 1.4, 1.0, 18.0), 2)
        confidence = round(
            _clamp((score / 100.0) * 0.6 + ((10.0 - min(atr_pct, 10.0)) / 10.0) * 0.4, 0.05, 0.95),
            2,
        )

        if score >= 75 and predicted_21d_return_pct > 3:
            recommendation = "STRONG_BUY"
        elif score >= 62 and predicted_21d_return_pct > 1:
            recommendation = "BUY"
        elif score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "AVOID"

        row_with_prediction = dict(row)
        row_with_prediction["prediction"] = {
            "horizon_days": 21,
            "predicted_return_pct": predicted_21d_return_pct,
            "projection": {
                "next_3d_return_pct": predicted_3d_return_pct,
                "next_5d_return_pct": predicted_5d_return_pct,
                "next_7d_return_pct": predicted_7d_return_pct,
                "next_21d_return_pct": predicted_21d_return_pct,
            },
            "downside_risk_pct": downside_risk_21d_pct,
            "confidence": confidence,
            "recommendation": recommendation,
        }
        enriched.append(row_with_prediction)
    return enriched


def build_top_picks(results: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    valid = [row for row in results if row.get("status") == "ok" and row.get("prediction")]
    ranked = sorted(
        valid,
        key=lambda row: (
            float(row["final_score"]),
            float(row["prediction"]["predicted_return_pct"]),
            float(row["prediction"]["confidence"]),
        ),
        reverse=True,
    )
    return ranked[: max(top_n, 1)]


def build_synthetic_portfolio(
    top_picks: list[dict[str, Any]],
    capital: float = 1_000_000.0,
    max_positions: int = 8,
    max_weight_per_position: float = 0.25,
) -> dict[str, Any]:
    selected = top_picks[: max_positions]
    if not selected:
        return {
            "capital": capital,
            "positions": [],
            "summary": {
                "positions_count": 0,
                "cash_remaining": capital,
                "expected_return_21d_pct": 0.0,
                "expected_pnl_21d": 0.0,
                "average_score": 0.0,
                "portfolio_confidence": 0.0,
                "diversification_index": 0.0,
            },
        }

    raw_weights = []
    for row in selected:
        score = float(row["final_score"])
        confidence = float(row["prediction"]["confidence"])
        atr_pct = float(row["diagnostics"].get("atr_pct", 10.0))
        risk_adjusted_strength = (score * confidence) / (1.0 + atr_pct / 10.0)
        raw_weights.append(max(risk_adjusted_strength, 0.001))

    raw_total = sum(raw_weights)
    normalized = [w / raw_total for w in raw_weights]
    capped = [min(w, max_weight_per_position) for w in normalized]
    cap_total = sum(capped)
    weights = [w / cap_total for w in capped]

    positions = []
    expected_return_21d_pct = 0.0
    average_score = 0.0
    confidence = 0.0
    hhi = 0.0
    for row, weight in zip(selected, weights):
        predicted_return = float(row["prediction"]["predicted_return_pct"])
        amount = round(capital * weight, 2)
        expected_return_21d_pct += weight * predicted_return
        average_score += weight * float(row["final_score"])
        confidence += weight * float(row["prediction"]["confidence"])
        hhi += weight * weight

        positions.append(
            {
                "ticker": row["ticker"],
                "weight": round(weight, 4),
                "allocation": amount,
                "final_score": row["final_score"],
                "recommendation": row["prediction"]["recommendation"],
                "predicted_return_21d_pct": predicted_return,
                "confidence": row["prediction"]["confidence"],
            }
        )

    expected_pnl = round(capital * (expected_return_21d_pct / 100.0), 2)
    diversification_index = round((1.0 / hhi) if hhi > 0 else 0.0, 2)
    return {
        "capital": capital,
        "positions": positions,
        "summary": {
            "positions_count": len(positions),
            "cash_remaining": 0.0,
            "expected_return_21d_pct": round(expected_return_21d_pct, 2),
            "expected_pnl_21d": expected_pnl,
            "average_score": round(average_score, 2),
            "portfolio_confidence": round(confidence, 2),
            "diversification_index": diversification_index,
        },
    }


def build_dashboard(
    enriched_results: list[dict[str, Any]],
    top_n: int,
    capital: float,
) -> dict[str, Any]:
    top_picks = build_top_picks(enriched_results, top_n=top_n)
    portfolio = build_synthetic_portfolio(top_picks=top_picks, capital=capital)

    valid = [row for row in enriched_results if row.get("status") == "ok"]
    total = len(enriched_results)
    valid_count = len(valid)
    avg_score = round(sum(float(row["final_score"]) for row in valid) / valid_count, 2) if valid_count else 0.0
    avg_pred_return = (
        round(sum(float(row["prediction"]["predicted_return_pct"]) for row in valid) / valid_count, 2)
        if valid_count
        else 0.0
    )
    avg_confidence = (
        round(sum(float(row["prediction"]["confidence"]) for row in valid) / valid_count, 2)
        if valid_count
        else 0.0
    )

    recommendation_mix = {
        "STRONG_BUY": 0,
        "BUY": 0,
        "HOLD": 0,
        "AVOID": 0,
    }
    for row in valid:
        recommendation_mix[row["prediction"]["recommendation"]] += 1

    return {
        "market_overview": {
            "coverage_tickers": total,
            "valid_tickers": valid_count,
            "error_tickers": total - valid_count,
            "average_steward_score": avg_score,
            "average_predicted_return_21d_pct": avg_pred_return,
            "average_confidence": avg_confidence,
            "recommendation_mix": recommendation_mix,
        },
        "top_picks": top_picks,
        "synthetic_portfolio": portfolio,
    }
