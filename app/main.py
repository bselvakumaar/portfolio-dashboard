import argparse
import logging
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.analytics import build_dashboard, build_top_picks, enrich_with_predictions
from app.auth_service import AuthService
from app.config import get_settings
from app.dashboard_ui_react import render_dashboard_html
from app.indicators import DataFetchError, calculate_indicators, fetch_ohlc_data
from app.market_snapshot import build_market_snapshot
from app.portfolio_service import analyze_portfolio
from app.scoring import compute_steward_score
from app.sentiment import SentimentEngine
from app.sheets_service import GoogleSheetsService
from app.trading_service import TradingService

settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name, version="1.0.0")
sentiment_engine = SentimentEngine(provider=settings.ai_sentiment_provider)
trading_service = TradingService(
    store_file=settings.trading_store_file,
    database_url=settings.trading_database_url,
    database_schema=settings.trading_database_schema,
    data_period=settings.data_period,
    data_interval=settings.data_interval,
    retry_attempts=settings.retry_attempts,
    retry_backoff_seconds=settings.retry_backoff_seconds,
    brokerage_rate=settings.trading_brokerage_rate,
    sell_charge_rate=settings.trading_sell_charge_rate,
    min_brokerage=settings.trading_min_brokerage,
)
auth_service = AuthService(
    database_url=settings.trading_database_url,
    database_schema=settings.trading_database_schema,
    jwt_secret=settings.jwt_secret,
    jwt_algorithm=settings.jwt_algorithm,
    jwt_exp_minutes=settings.jwt_exp_minutes,
    superadmin_email=settings.superadmin_email,
    superadmin_password=settings.superadmin_password,
)
security = HTTPBearer(auto_error=False)


class RunRequest(BaseModel):
    tickers: list[str] | None = Field(default=None, description="NSE tickers with .NS suffix")
    push_to_sheets: bool = True


class DashboardRequest(BaseModel):
    tickers: list[str] | None = Field(default=None, description="NSE tickers with .NS suffix")
    top_n: int = Field(default=5, ge=1, le=20)
    capital: float = Field(default=1_000_000.0, gt=0)
    push_to_sheets: bool = False


class PortfolioHolding(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    avg_price: float = Field(default=0.0, ge=0.0)


class PortfolioRequest(BaseModel):
    holdings: list[PortfolioHolding]


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    full_name: str = ""


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TradingAccountCreateRequest(BaseModel):
    initial_funds: float = Field(default=0.0, ge=0.0)


class TradingFundRequest(BaseModel):
    amount: float = Field(gt=0.0)


class TradingOrderRequest(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0.0)
    price: float | None = Field(default=None, gt=0.0)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        return auth_service.verify_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_superadmin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")
    return user


def require_trade_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user.get("role") == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin is read-only and cannot edit user trading data",
        )
    return user


def _build_sheet_rows(results: list[dict[str, Any]]) -> list[list[object]]:
    headers = [
        "as_of_utc",
        "ticker",
        "final_score",
        "momentum",
        "trend_strength",
        "volume_strength",
        "rsi_strength",
        "volatility_control",
        "ai_sentiment",
        "sentiment_score_raw",
        "close",
        "rsi_14",
        "sma_20",
        "sma_50",
        "macd",
        "atr_14",
        "high_proximity_pct",
        "volume_spike_ratio",
        "status",
        "error",
    ]
    rows = [headers]
    for row in results:
        components = row.get("components", {})
        indicators = row.get("indicators", {})
        rows.append(
            [
                row.get("as_of_utc"),
                row.get("ticker"),
                row.get("final_score"),
                components.get("momentum"),
                components.get("trend_strength"),
                components.get("volume_strength"),
                components.get("rsi_strength"),
                components.get("volatility_control"),
                components.get("ai_sentiment"),
                row.get("sentiment_score_raw"),
                indicators.get("close"),
                indicators.get("rsi_14"),
                indicators.get("sma_20"),
                indicators.get("sma_50"),
                indicators.get("macd"),
                indicators.get("atr_14"),
                indicators.get("high_proximity_pct"),
                indicators.get("volume_spike_ratio"),
                row.get("status"),
                row.get("error", ""),
            ]
        )
    return rows


def run_scoring_pipeline(tickers: list[str], push_to_sheets: bool) -> dict[str, Any]:
    as_of = datetime.now(tz=timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for ticker in tickers:
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            continue
        logger.info("Starting scoring", extra={"ticker": normalized_ticker})
        try:
            ohlc = fetch_ohlc_data(
                ticker=normalized_ticker,
                period=settings.data_period,
                interval=settings.data_interval,
                retry_attempts=settings.retry_attempts,
                retry_backoff_seconds=settings.retry_backoff_seconds,
            )
            indicator_values = calculate_indicators(ohlc)
            sentiment_value = sentiment_engine.get_sentiment_score(normalized_ticker)
            score_payload = compute_steward_score(
                indicators=indicator_values,
                sentiment_score=sentiment_value,
                weights=settings.scoring_weights,
            )

            results.append(
                {
                    "as_of_utc": as_of,
                    "ticker": normalized_ticker,
                    "status": "ok",
                    "final_score": score_payload["final_score"],
                    "components": score_payload["components"],
                    "diagnostics": score_payload["diagnostics"],
                    "sentiment_score_raw": sentiment_value,
                    "indicators": indicator_values,
                }
            )
        except (DataFetchError, ValueError) as exc:
            logger.error("Scoring failed for ticker", exc_info=True, extra={"ticker": normalized_ticker})
            results.append(
                {
                    "as_of_utc": as_of,
                    "ticker": normalized_ticker,
                    "status": "error",
                    "final_score": 0.0,
                    "components": {},
                    "diagnostics": {},
                    "sentiment_score_raw": 0.0,
                    "indicators": {},
                    "error": str(exc),
                }
            )

    sheet_update_status: dict[str, Any] = {"updated": False, "reason": "disabled"}
    should_push = push_to_sheets and settings.enable_sheets_update
    if should_push:
        try:
            sheet_service = GoogleSheetsService(
                sheets_id=settings.google_sheets_id,
                target_range=settings.google_sheets_range,
                service_account_file=settings.google_service_account_file,
                service_account_json=settings.google_service_account_json,
            )
            sheet_update_status = sheet_service.batch_update_rows(_build_sheet_rows(results))
        except Exception as exc:
            logger.error("Google Sheets update failed", exc_info=True)
            sheet_update_status = {"updated": False, "reason": str(exc)}

    return {
        "as_of_utc": as_of,
        "requested_tickers": tickers,
        "result_count": len(results),
        "results": results,
        "sheets": sheet_update_status,
    }


def run_dashboard_pipeline(
    tickers: list[str],
    top_n: int,
    capital: float,
    push_to_sheets: bool,
) -> dict[str, Any]:
    base = run_scoring_pipeline(tickers=tickers, push_to_sheets=push_to_sheets)
    enriched_results = enrich_with_predictions(base["results"])
    dashboard = build_dashboard(enriched_results=enriched_results, top_n=top_n, capital=capital)
    return {
        "as_of_utc": base["as_of_utc"],
        "requested_tickers": base["requested_tickers"],
        "result_count": base["result_count"],
        "sheets": base["sheets"],
        "market_overview": dashboard["market_overview"],
        "top_picks": dashboard["top_picks"],
        "synthetic_portfolio": dashboard["synthetic_portfolio"],
        "results": enriched_results,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.app_env}


@app.post("/run")
def run(request: RunRequest) -> dict[str, Any]:
    tickers = request.tickers or settings.default_tickers
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")
    return run_scoring_pipeline(tickers=tickers, push_to_sheets=request.push_to_sheets)


@app.get("/run")
def run_default() -> dict[str, Any]:
    if not settings.default_tickers:
        raise HTTPException(status_code=400, detail="DEFAULT_TICKERS is empty")
    return run_scoring_pipeline(tickers=settings.default_tickers, push_to_sheets=True)


@app.post("/dashboard")
def dashboard(request: DashboardRequest) -> dict[str, Any]:
    tickers = request.tickers or settings.default_tickers
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")
    return run_dashboard_pipeline(
        tickers=tickers,
        top_n=request.top_n,
        capital=request.capital,
        push_to_sheets=request.push_to_sheets,
    )


@app.get("/dashboard")
def dashboard_default() -> dict[str, Any]:
    if not settings.default_tickers:
        raise HTTPException(status_code=400, detail="DEFAULT_TICKERS is empty")
    return run_dashboard_pipeline(
        tickers=settings.default_tickers,
        top_n=5,
        capital=1_000_000.0,
        push_to_sheets=False,
    )


@app.get("/dashboard/ui", response_class=HTMLResponse)
def dashboard_ui() -> str:
    return render_dashboard_html()


@app.get("/top-picks")
def top_picks(top_n: int = 5) -> dict[str, Any]:
    if not settings.default_tickers:
        raise HTTPException(status_code=400, detail="DEFAULT_TICKERS is empty")
    base = run_scoring_pipeline(tickers=settings.default_tickers, push_to_sheets=False)
    enriched = enrich_with_predictions(base["results"])
    return {
        "as_of_utc": base["as_of_utc"],
        "requested_tickers": settings.default_tickers,
        "top_n": top_n,
        "top_picks": build_top_picks(enriched, top_n=top_n),
    }


@app.get("/market/snapshot")
def market_snapshot(top_n: int = 10) -> dict[str, Any]:
    n = max(1, min(top_n, 20))
    return build_market_snapshot(
        tickers=settings.market_snapshot_universe,
        top_n=n,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
    )


@app.post("/portfolio/analyze")
def portfolio_analyze(request: PortfolioRequest) -> dict[str, Any]:
    if not request.holdings:
        raise HTTPException(status_code=400, detail="Holdings are required")

    tickers = [h.ticker.strip().upper() for h in request.holdings if h.ticker.strip()]
    dashboard_result = run_dashboard_pipeline(
        tickers=tickers,
        top_n=min(5, max(1, len(tickers))),
        capital=1_000_000.0,
        push_to_sheets=False,
    )
    scored_map = {row["ticker"]: row for row in dashboard_result["results"]}
    portfolio_result = analyze_portfolio(
        holdings=[h.model_dump() for h in request.holdings],
        scored_rows=scored_map,
    )
    return {
        "as_of_utc": dashboard_result["as_of_utc"],
        "portfolio": portfolio_result,
    }


@app.post("/auth/register")
def auth_register(request: AuthRegisterRequest) -> dict[str, Any]:
    try:
        user = auth_service.register_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
        )
        return {"user": user}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/login")
def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
    try:
        return auth_service.login(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/me")
def auth_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": current_user}


@app.post("/trading/account/create")
def trading_account_create(
    request: TradingAccountCreateRequest,
    current_user: dict[str, Any] = Depends(require_trade_user),
) -> dict[str, Any]:
    try:
        return trading_service.create_account(
            user_id=current_user["email"],
            initial_funds=request.initial_funds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/trading/account/me")
def trading_account_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return trading_service.account_snapshot(user_id=current_user["email"])


@app.get("/trading/account/{user_id}")
def trading_account_snapshot(
    user_id: str,
    _: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, Any]:
    return trading_service.account_snapshot(user_id=user_id.strip().lower())


@app.post("/trading/funds/add")
def trading_funds_add(
    request: TradingFundRequest,
    current_user: dict[str, Any] = Depends(require_trade_user),
) -> dict[str, Any]:
    try:
        return trading_service.add_funds(
            user_id=current_user["email"],
            amount=request.amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/trading/order/buy")
def trading_order_buy(
    request: TradingOrderRequest,
    current_user: dict[str, Any] = Depends(require_trade_user),
) -> dict[str, Any]:
    try:
        return trading_service.buy(
            user_id=current_user["email"],
            ticker=request.ticker,
            quantity=request.quantity,
            price=request.price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/trading/order/sell")
def trading_order_sell(
    request: TradingOrderRequest,
    current_user: dict[str, Any] = Depends(require_trade_user),
) -> dict[str, Any]:
    try:
        return trading_service.sell(
            user_id=current_user["email"],
            ticker=request.ticker,
            quantity=request.quantity,
            price=request.price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/admin/trading/overview")
def admin_trading_overview(
    _: dict[str, Any] = Depends(require_superadmin),
) -> dict[str, Any]:
    return trading_service.admin_overview()


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Steward Quant scoring runner")
    parser.add_argument(
        "--tickers",
        type=str,
        default="",
        help="Comma-separated list of NSE tickers with .NS suffix",
    )
    parser.add_argument(
        "--no-sheets",
        action="store_true",
        help="Disable Google Sheets push for this run",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run FastAPI server instead of one-off batch run",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Run full dashboard pipeline with predictions and synthetic portfolio",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Top picks count for dashboard mode",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1_000_000.0,
        help="Synthetic capital for portfolio construction",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_cli_args()
    if args.serve:
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
        return

    tickers = (
        [item.strip().upper() for item in args.tickers.split(",") if item.strip()]
        if args.tickers
        else settings.default_tickers
    )
    if args.dashboard:
        result = run_dashboard_pipeline(
            tickers=tickers,
            top_n=max(args.top_n, 1),
            capital=max(args.capital, 1.0),
            push_to_sheets=not args.no_sheets,
        )
        logger.info(
            "CLI dashboard run complete",
            extra={
                "result_count": result["result_count"],
                "top_picks_count": len(result["top_picks"]),
                "portfolio_summary": result["synthetic_portfolio"]["summary"],
                "sheets": result["sheets"],
            },
        )
        return

    result = run_scoring_pipeline(tickers=tickers, push_to_sheets=not args.no_sheets)
    logger.info("CLI run complete", extra={"result_count": result["result_count"], "sheets": result["sheets"]})


if __name__ == "__main__":
    main()
