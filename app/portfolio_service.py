from typing import Any


def analyze_portfolio(
    holdings: list[dict[str, Any]],
    scored_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    positions: list[dict[str, Any]] = []
    invested = 0.0
    market_value = 0.0
    expected_pnl_7d = 0.0
    expected_pnl_21d = 0.0

    for holding in holdings:
        ticker = str(holding["ticker"]).strip().upper()
        quantity = float(holding["quantity"])
        avg_price = float(holding.get("avg_price", 0.0))
        matched = scored_rows.get(ticker)
        if not matched or matched.get("status") != "ok":
            continue

        close = float(matched["indicators"]["close"])
        invested_amount = quantity * avg_price if avg_price > 0 else quantity * close
        current_value = quantity * close
        pnl = current_value - invested_amount
        pred = matched["prediction"]
        proj = pred["projection"]
        est_7d = current_value * (float(proj["next_7d_return_pct"]) / 100.0)
        est_21d = current_value * (float(proj["next_21d_return_pct"]) / 100.0)

        invested += invested_amount
        market_value += current_value
        expected_pnl_7d += est_7d
        expected_pnl_21d += est_21d

        positions.append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "avg_price": round(avg_price, 2),
                "current_price": round(close, 2),
                "invested_amount": round(invested_amount, 2),
                "current_value": round(current_value, 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round((pnl / invested_amount) * 100.0, 2) if invested_amount else 0.0,
                "final_score": matched["final_score"],
                "recommendation": pred["recommendation"],
                "confidence": pred["confidence"],
                "projection": proj,
            }
        )

    positions.sort(key=lambda x: x["current_value"], reverse=True)
    summary = {
        "positions_count": len(positions),
        "total_invested": round(invested, 2),
        "total_current_value": round(market_value, 2),
        "total_unrealized_pnl": round(market_value - invested, 2),
        "total_unrealized_pnl_pct": round(((market_value - invested) / invested) * 100.0, 2) if invested else 0.0,
        "expected_pnl_next_7d": round(expected_pnl_7d, 2),
        "expected_pnl_next_21d": round(expected_pnl_21d, 2),
    }
    return {"summary": summary, "positions": positions}
