import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
import secrets

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _load_scoring_weights() -> dict[str, float]:
    default_weights = {
        "momentum": 30.0,
        "trend_strength": 20.0,
        "volume_strength": 20.0,
        "rsi_strength": 10.0,
        "volatility_control": 10.0,
        "ai_sentiment": 10.0,
    }
    raw = os.getenv("SCORING_WEIGHTS_JSON")
    if not raw:
        return default_weights
    parsed = json.loads(raw)
    merged = default_weights.copy()
    merged.update({k: float(v) for k, v in parsed.items()})
    return merged


def _decrypt_fernet_value(encrypted_value: str, encryption_key: str) -> str:
    try:
        from cryptography.fernet import Fernet
    except Exception as exc:
        raise ValueError("cryptography dependency is required for encrypted secrets") from exc
    try:
        cipher = Fernet(encryption_key.encode("utf-8"))
        return cipher.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise ValueError("Failed to decrypt TRADING_DATABASE_URL_ENCRYPTED") from exc


def _load_trading_database_url() -> str:
    direct = os.getenv("TRADING_DATABASE_URL", "").strip()
    if direct:
        return direct
    encrypted = os.getenv("TRADING_DATABASE_URL_ENCRYPTED", "").strip()
    encryption_key = os.getenv("APP_ENCRYPTION_KEY", "").strip()
    if encrypted and encryption_key:
        return _decrypt_fernet_value(encrypted, encryption_key)
    return ""


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Steward Quant Intelligence Platform")
    app_env: str = os.getenv("APP_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _get_int("PORT", 8080)

    default_tickers: list[str] = field(
        default_factory=lambda: _get_list(
            "DEFAULT_TICKERS", ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
        )
    )
    data_period: str = os.getenv("DATA_PERIOD", "6mo")
    data_interval: str = os.getenv("DATA_INTERVAL", "1d")
    retry_attempts: int = _get_int("RETRY_ATTEMPTS", 3)
    retry_backoff_seconds: float = _get_float("RETRY_BACKOFF_SECONDS", 1.5)
    market_snapshot_universe: list[str] = field(
        default_factory=lambda: _get_list(
            "MARKET_SNAPSHOT_UNIVERSE",
            [
                "RELIANCE.NS",
                "TCS.NS",
                "HDFCBANK.NS",
                "INFY.NS",
                "ICICIBANK.NS",
                "ITC.NS",
                "LT.NS",
                "SBIN.NS",
                "AXISBANK.NS",
                "KOTAKBANK.NS",
                "BHARTIARTL.NS",
                "HINDUNILVR.NS",
                "BAJFINANCE.NS",
                "MARUTI.NS",
                "TITAN.NS",
                "ASIANPAINT.NS",
                "WIPRO.NS",
                "HCLTECH.NS",
                "SUNPHARMA.NS",
                "NTPC.NS",
            ],
        )
    )

    scoring_weights: dict[str, float] = field(default_factory=_load_scoring_weights)

    ai_sentiment_provider: str = os.getenv("AI_SENTIMENT_PROVIDER", "stub")

    enable_sheets_update: bool = _get_bool("ENABLE_SHEETS_UPDATE", True)
    google_sheets_id: str = os.getenv("GOOGLE_SHEETS_ID", "")
    google_sheets_range: str = os.getenv("GOOGLE_SHEETS_RANGE", "Scores!A1")
    google_service_account_file: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    trading_store_file: str = os.getenv("TRADING_STORE_FILE", "app/data/trading_store.json")
    trading_database_url: str = field(default_factory=_load_trading_database_url)
    trading_database_schema: str = os.getenv("TRADING_DATABASE_SCHEMA", "stock-dashboard")
    trading_brokerage_rate: float = _get_float("TRADING_BROKERAGE_RATE", 0.001)
    trading_sell_charge_rate: float = _get_float("TRADING_SELL_CHARGE_RATE", 0.0015)
    trading_min_brokerage: float = _get_float("TRADING_MIN_BROKERAGE", 20.0)
    jwt_secret: str = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_exp_minutes: int = _get_int("JWT_EXP_MINUTES", 720)
    superadmin_email: str = os.getenv("SUPERADMIN_EMAIL", "admin@steward.local")
    superadmin_password: str = os.getenv("SUPERADMIN_PASSWORD", "ChangeMeNow#123")


class JsonFormatter(logging.Formatter):
    """Minimal structured formatter for Cloud Run-friendly JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    configure_logging(settings.log_level)
    return settings
