import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.indicators import calculate_indicators, fetch_ohlc_data

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency during local compile.
    psycopg = None  # type: ignore[assignment]


class TradingService:
    def __init__(
        self,
        store_file: str,
        data_period: str,
        data_interval: str,
        retry_attempts: int,
        retry_backoff_seconds: float,
        brokerage_rate: float,
        sell_charge_rate: float,
        min_brokerage: float,
        database_url: str = "",
        database_schema: str = "stock-dashboard",
    ) -> None:
        self.store_path = Path(store_file)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_period = data_period
        self.data_interval = data_interval
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.brokerage_rate = brokerage_rate
        self.sell_charge_rate = sell_charge_rate
        self.min_brokerage = min_brokerage
        self.database_url = self._normalize_database_url(database_url.strip())
        self.database_schema = database_schema.strip() or "stock-dashboard"
        self._qschema = f'"{self.database_schema.replace(chr(34), chr(34) * 2)}"'
        self._lock = threading.RLock()
        self._db_enabled = bool(
            self.database_url
            and psycopg is not None
            and (self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://"))
        )
        self._db_init_error: str | None = None

        if self._db_enabled:
            try:
                self._init_db()
            except Exception as exc:
                self._db_enabled = False
                self._db_init_error = str(exc)
        if not self.store_path.exists():
            self._write_store({"users": {}})

    def _normalize_database_url(self, url: str) -> str:
        if not url:
            return ""
        # Supports values such as: postgresql://postgres:'pass@123'@host:5432/postgres
        single_quoted_pw = re.search(r":'([^']*)'@", url)
        if single_quoted_pw:
            password = quote(single_quoted_pw.group(1), safe="")
            return url.replace(single_quoted_pw.group(0), f":{password}@", 1)
        return url

    def _connect(self):
        if not self._db_enabled:
            raise RuntimeError("Database mode is not enabled")
        return psycopg.connect(self.database_url)  # type: ignore[union-attr]

    def _init_db(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self._qschema}")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qschema}.trading_accounts (
                      user_id TEXT PRIMARY KEY,
                      cash_balance DOUBLE PRECISION NOT NULL DEFAULT 0,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qschema}.trading_holdings (
                      user_id TEXT NOT NULL,
                      ticker TEXT NOT NULL,
                      quantity DOUBLE PRECISION NOT NULL,
                      avg_price DOUBLE PRECISION NOT NULL,
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                      PRIMARY KEY (user_id, ticker)
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qschema}.trading_transactions (
                      id BIGSERIAL PRIMARY KEY,
                      user_id TEXT NOT NULL,
                      time_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                      type TEXT NOT NULL,
                      ticker TEXT,
                      quantity DOUBLE PRECISION,
                      price DOUBLE PRECISION,
                      notional DOUBLE PRECISION,
                      charges DOUBLE PRECISION,
                      amount DOUBLE PRECISION,
                      cash_balance_after DOUBLE PRECISION,
                      metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb
                    )
                    """
                )
            conn.commit()

    def _now_iso(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    def _read_store(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"users": {}}
        with self.store_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write_store(self, data: dict[str, Any]) -> None:
        with self.store_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=True, indent=2)

    def _ensure_user_json(self, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        users = data.setdefault("users", {})
        if user_id not in users:
            users[user_id] = {
                "created_at": self._now_iso(),
                "cash_balance": 0.0,
                "holdings": {},
                "transactions": [],
            }
        return users[user_id]

    def _ensure_user_db(self, cur, user_id: str) -> None:
        cur.execute(
            f"""
            INSERT INTO {self._qschema}.trading_accounts (user_id, cash_balance)
            VALUES (%s, 0)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id,),
        )

    def _get_price(self, ticker: str) -> float:
        ohlc = fetch_ohlc_data(
            ticker=ticker,
            period=self.data_period,
            interval=self.data_interval,
            retry_attempts=self.retry_attempts,
            retry_backoff_seconds=self.retry_backoff_seconds,
        )
        indicators = calculate_indicators(ohlc)
        return float(indicators["close"])

    def create_account(self, user_id: str, initial_funds: float = 0.0) -> dict[str, Any]:
        if initial_funds < 0:
            raise ValueError("initial_funds cannot be negative")
        if self._db_enabled:
            return self._create_account_db(user_id, initial_funds)
        return self._create_account_json(user_id, initial_funds)

    def _create_account_json(self, user_id: str, initial_funds: float = 0.0) -> dict[str, Any]:
        with self._lock:
            data = self._read_store()
            user = self._ensure_user_json(data, user_id)
            if initial_funds > 0:
                user["cash_balance"] = float(user["cash_balance"]) + float(initial_funds)
                user["transactions"].append(
                    {
                        "time_utc": self._now_iso(),
                        "type": "fund_add",
                        "amount": round(float(initial_funds), 2),
                        "note": "Initial funding",
                    }
                )
            self._write_store(data)
            return self.account_snapshot(user_id=user_id, _data=data)

    def _create_account_db(self, user_id: str, initial_funds: float = 0.0) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_db(cur, user_id)
                if initial_funds > 0:
                    cur.execute(
                        f"""
                        UPDATE {self._qschema}.trading_accounts
                        SET cash_balance = cash_balance + %s, updated_at = NOW()
                        WHERE user_id = %s
                        """,
                        (float(initial_funds), user_id),
                    )
                    cur.execute(
                        f"""
                        INSERT INTO {self._qschema}.trading_transactions
                        (user_id, type, amount, cash_balance_after, metadata)
                        SELECT user_id, 'fund_add', %s, cash_balance, %s::jsonb
                        FROM {self._qschema}.trading_accounts
                        WHERE user_id = %s
                        """,
                        (float(initial_funds), json.dumps({"note": "Initial funding"}), user_id),
                    )
            conn.commit()
        return self.account_snapshot(user_id=user_id)

    def add_funds(self, user_id: str, amount: float) -> dict[str, Any]:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        if self._db_enabled:
            return self._add_funds_db(user_id, amount)
        return self._add_funds_json(user_id, amount)

    def _add_funds_json(self, user_id: str, amount: float) -> dict[str, Any]:
        with self._lock:
            data = self._read_store()
            user = self._ensure_user_json(data, user_id)
            user["cash_balance"] = float(user["cash_balance"]) + float(amount)
            user["transactions"].append(
                {
                    "time_utc": self._now_iso(),
                    "type": "fund_add",
                    "amount": round(float(amount), 2),
                    "cash_balance_after": round(float(user["cash_balance"]), 2),
                }
            )
            self._write_store(data)
            return self.account_snapshot(user_id=user_id, _data=data)

    def _add_funds_db(self, user_id: str, amount: float) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_db(cur, user_id)
                cur.execute(
                    f"""
                    UPDATE {self._qschema}.trading_accounts
                    SET cash_balance = cash_balance + %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (float(amount), user_id),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qschema}.trading_transactions
                    (user_id, type, amount, cash_balance_after)
                    SELECT user_id, 'fund_add', %s, cash_balance
                    FROM {self._qschema}.trading_accounts
                    WHERE user_id = %s
                    """,
                    (float(amount), user_id),
                )
            conn.commit()
        return self.account_snapshot(user_id=user_id)

    def buy(self, user_id: str, ticker: str, quantity: float, price: float | None = None) -> dict[str, Any]:
        normalized_ticker = ticker.strip().upper()
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        execution_price = float(price) if price and price > 0 else self._get_price(normalized_ticker)
        if self._db_enabled:
            return self._buy_db(user_id, normalized_ticker, quantity, execution_price)
        return self._buy_json(user_id, normalized_ticker, quantity, execution_price)

    def _buy_json(self, user_id: str, ticker: str, quantity: float, execution_price: float) -> dict[str, Any]:
        with self._lock:
            data = self._read_store()
            user = self._ensure_user_json(data, user_id)
            notional = float(quantity) * execution_price
            brokerage = max(self.min_brokerage, notional * self.brokerage_rate)
            total_cost = notional + brokerage
            if float(user["cash_balance"]) < total_cost:
                raise ValueError("Insufficient funds")

            holdings = user.setdefault("holdings", {})
            existing = holdings.get(ticker, {"quantity": 0.0, "avg_price": 0.0})
            old_qty = float(existing["quantity"])
            new_qty = old_qty + float(quantity)
            old_cost = old_qty * float(existing["avg_price"])
            new_avg = (old_cost + notional) / new_qty if new_qty > 0 else 0.0
            holdings[ticker] = {"quantity": round(new_qty, 6), "avg_price": round(new_avg, 4)}

            user["cash_balance"] = float(user["cash_balance"]) - total_cost
            user["transactions"].append(
                {
                    "time_utc": self._now_iso(),
                    "type": "buy",
                    "ticker": ticker,
                    "quantity": round(float(quantity), 6),
                    "price": round(execution_price, 4),
                    "notional": round(notional, 2),
                    "charges": round(brokerage, 2),
                    "total_debit": round(total_cost, 2),
                    "cash_balance_after": round(float(user["cash_balance"]), 2),
                }
            )
            self._write_store(data)
            return self.account_snapshot(user_id=user_id, _data=data)

    def _buy_db(self, user_id: str, ticker: str, quantity: float, execution_price: float) -> dict[str, Any]:
        notional = float(quantity) * execution_price
        brokerage = max(self.min_brokerage, notional * self.brokerage_rate)
        total_cost = notional + brokerage
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_db(cur, user_id)
                cur.execute(
                    f"SELECT cash_balance FROM {self._qschema}.trading_accounts WHERE user_id = %s FOR UPDATE",
                    (user_id,),
                )
                row = cur.fetchone()
                current_cash = float(row[0]) if row else 0.0
                if current_cash < total_cost:
                    raise ValueError("Insufficient funds")

                cur.execute(
                    f"SELECT quantity, avg_price FROM {self._qschema}.trading_holdings WHERE user_id=%s AND ticker=%s",
                    (user_id, ticker),
                )
                existing = cur.fetchone()
                old_qty = float(existing[0]) if existing else 0.0
                old_avg = float(existing[1]) if existing else 0.0
                new_qty = old_qty + float(quantity)
                new_avg = ((old_qty * old_avg) + notional) / new_qty

                cur.execute(
                    f"""
                    INSERT INTO {self._qschema}.trading_holdings (user_id, ticker, quantity, avg_price)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, ticker)
                    DO UPDATE SET quantity = EXCLUDED.quantity, avg_price = EXCLUDED.avg_price, updated_at = NOW()
                    """,
                    (user_id, ticker, new_qty, new_avg),
                )
                cur.execute(
                    f"""
                    UPDATE {self._qschema}.trading_accounts
                    SET cash_balance = cash_balance - %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (total_cost, user_id),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qschema}.trading_transactions
                    (user_id, type, ticker, quantity, price, notional, charges, amount, cash_balance_after)
                    SELECT user_id, 'buy', %s, %s, %s, %s, %s, %s, cash_balance
                    FROM {self._qschema}.trading_accounts
                    WHERE user_id = %s
                    """,
                    (ticker, quantity, execution_price, notional, brokerage, -total_cost, user_id),
                )
            conn.commit()
        return self.account_snapshot(user_id=user_id)

    def sell(self, user_id: str, ticker: str, quantity: float, price: float | None = None) -> dict[str, Any]:
        normalized_ticker = ticker.strip().upper()
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        execution_price = float(price) if price and price > 0 else self._get_price(normalized_ticker)
        if self._db_enabled:
            return self._sell_db(user_id, normalized_ticker, quantity, execution_price)
        return self._sell_json(user_id, normalized_ticker, quantity, execution_price)

    def _sell_json(self, user_id: str, ticker: str, quantity: float, execution_price: float) -> dict[str, Any]:
        with self._lock:
            data = self._read_store()
            user = self._ensure_user_json(data, user_id)
            holdings = user.setdefault("holdings", {})
            existing = holdings.get(ticker)
            if not existing or float(existing["quantity"]) < float(quantity):
                raise ValueError("Insufficient quantity to sell")

            notional = float(quantity) * execution_price
            brokerage = max(self.min_brokerage, notional * self.brokerage_rate)
            sell_charges = brokerage + (notional * self.sell_charge_rate)
            net_credit = notional - sell_charges

            remaining = float(existing["quantity"]) - float(quantity)
            if remaining <= 0:
                holdings.pop(ticker, None)
            else:
                holdings[ticker] = {
                    "quantity": round(remaining, 6),
                    "avg_price": round(float(existing["avg_price"]), 4),
                }

            user["cash_balance"] = float(user["cash_balance"]) + net_credit
            user["transactions"].append(
                {
                    "time_utc": self._now_iso(),
                    "type": "sell",
                    "ticker": ticker,
                    "quantity": round(float(quantity), 6),
                    "price": round(execution_price, 4),
                    "notional": round(notional, 2),
                    "charges": round(sell_charges, 2),
                    "net_credit": round(net_credit, 2),
                    "cash_balance_after": round(float(user["cash_balance"]), 2),
                }
            )
            self._write_store(data)
            return self.account_snapshot(user_id=user_id, _data=data)

    def _sell_db(self, user_id: str, ticker: str, quantity: float, execution_price: float) -> dict[str, Any]:
        notional = float(quantity) * execution_price
        brokerage = max(self.min_brokerage, notional * self.brokerage_rate)
        sell_charges = brokerage + (notional * self.sell_charge_rate)
        net_credit = notional - sell_charges
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_db(cur, user_id)
                cur.execute(
                    f"""
                    SELECT quantity, avg_price
                    FROM {self._qschema}.trading_holdings
                    WHERE user_id = %s AND ticker = %s
                    FOR UPDATE
                    """,
                    (user_id, ticker),
                )
                row = cur.fetchone()
                if not row or float(row[0]) < float(quantity):
                    raise ValueError("Insufficient quantity to sell")
                remaining = float(row[0]) - float(quantity)
                avg_price = float(row[1])

                if remaining <= 0:
                    cur.execute(
                        f"DELETE FROM {self._qschema}.trading_holdings WHERE user_id=%s AND ticker=%s",
                        (user_id, ticker),
                    )
                else:
                    cur.execute(
                        f"""
                        UPDATE {self._qschema}.trading_holdings
                        SET quantity = %s, avg_price = %s, updated_at = NOW()
                        WHERE user_id = %s AND ticker = %s
                        """,
                        (remaining, avg_price, user_id, ticker),
                    )

                cur.execute(
                    f"""
                    UPDATE {self._qschema}.trading_accounts
                    SET cash_balance = cash_balance + %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (net_credit, user_id),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qschema}.trading_transactions
                    (user_id, type, ticker, quantity, price, notional, charges, amount, cash_balance_after)
                    SELECT user_id, 'sell', %s, %s, %s, %s, %s, %s, cash_balance
                    FROM {self._qschema}.trading_accounts
                    WHERE user_id = %s
                    """,
                    (ticker, quantity, execution_price, notional, sell_charges, net_credit, user_id),
                )
            conn.commit()
        return self.account_snapshot(user_id=user_id)

    def account_snapshot(self, user_id: str, _data: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._db_enabled:
            return self._account_snapshot_db(user_id)
        return self._account_snapshot_json(user_id, _data)

    def _account_snapshot_json(self, user_id: str, _data: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            data = _data if _data is not None else self._read_store()
            user = self._ensure_user_json(data, user_id)
            holdings = [
                {
                    "ticker": ticker,
                    "quantity": float(value["quantity"]),
                    "avg_price": float(value["avg_price"]),
                }
                for ticker, value in sorted(user.get("holdings", {}).items())
            ]
            transactions = list(user.get("transactions", []))[-100:]
            return {
                "user_id": user_id,
                "cash_balance": round(float(user.get("cash_balance", 0.0)), 2),
                "holdings": holdings,
                "holdings_count": len(holdings),
                "transactions": transactions,
                "transaction_count": len(user.get("transactions", [])),
                "charges_config": {
                    "brokerage_rate": self.brokerage_rate,
                    "sell_charge_rate": self.sell_charge_rate,
                    "min_brokerage": self.min_brokerage,
                },
                "storage_backend": "json",
                "database_fallback_error": self._db_init_error,
            }

    def _account_snapshot_db(self, user_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                self._ensure_user_db(cur, user_id)
                cur.execute(
                    f"SELECT cash_balance FROM {self._qschema}.trading_accounts WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                cash_balance = float(row[0]) if row else 0.0
                cur.execute(
                    f"""
                    SELECT ticker, quantity, avg_price
                    FROM {self._qschema}.trading_holdings
                    WHERE user_id = %s
                    ORDER BY ticker
                    """,
                    (user_id,),
                )
                holdings = [
                    {"ticker": item[0], "quantity": float(item[1]), "avg_price": float(item[2])}
                    for item in cur.fetchall()
                ]
                cur.execute(
                    f"""
                    SELECT time_utc, type, ticker, quantity, price, notional, charges, amount, cash_balance_after, metadata
                    FROM {self._qschema}.trading_transactions
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT 100
                    """,
                    (user_id,),
                )
                txns_raw = cur.fetchall()
                txns = []
                for item in txns_raw:
                    txns.append(
                        {
                            "time_utc": item[0].isoformat() if item[0] else None,
                            "type": item[1],
                            "ticker": item[2],
                            "quantity": item[3],
                            "price": item[4],
                            "notional": item[5],
                            "charges": item[6],
                            "amount": item[7],
                            "cash_balance_after": item[8],
                            **(item[9] or {}),
                        }
                    )
                cur.execute(
                    f"SELECT COUNT(*) FROM {self._qschema}.trading_transactions WHERE user_id = %s",
                    (user_id,),
                )
                transaction_count = int(cur.fetchone()[0])
            conn.commit()
        txns.reverse()
        return {
            "user_id": user_id,
            "cash_balance": round(cash_balance, 2),
            "holdings": holdings,
            "holdings_count": len(holdings),
            "transactions": txns,
            "transaction_count": transaction_count,
            "charges_config": {
                "brokerage_rate": self.brokerage_rate,
                "sell_charge_rate": self.sell_charge_rate,
                "min_brokerage": self.min_brokerage,
            },
            "storage_backend": "postgres",
            "schema": self.database_schema,
        }

    def admin_overview(self) -> dict[str, Any]:
        if not self._db_enabled:
            data = self._read_store()
            users = data.get("users", {})
            rows = []
            for uid, user in users.items():
                holdings_count = len((user or {}).get("holdings", {}))
                rows.append(
                    {
                        "user_id": uid,
                        "cash_balance": round(float((user or {}).get("cash_balance", 0.0)), 2),
                        "holdings_count": holdings_count,
                        "transaction_count": len((user or {}).get("transactions", [])),
                    }
                )
            return {
                "users": rows,
                "total_users": len(rows),
                "storage_backend": "json",
                "database_fallback_error": self._db_init_error,
            }

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT a.user_id,
                           a.cash_balance,
                           COALESCE(h.holdings_count, 0) AS holdings_count,
                           COALESCE(t.transaction_count, 0) AS transaction_count
                    FROM {self._qschema}.trading_accounts a
                    LEFT JOIN (
                        SELECT user_id, COUNT(*) AS holdings_count
                        FROM {self._qschema}.trading_holdings
                        GROUP BY user_id
                    ) h ON h.user_id = a.user_id
                    LEFT JOIN (
                        SELECT user_id, COUNT(*) AS transaction_count
                        FROM {self._qschema}.trading_transactions
                        GROUP BY user_id
                    ) t ON t.user_id = a.user_id
                    ORDER BY a.user_id
                    """
                )
                rows = [
                    {
                        "user_id": row[0],
                        "cash_balance": round(float(row[1]), 2),
                        "holdings_count": int(row[2]),
                        "transaction_count": int(row[3]),
                    }
                    for row in cur.fetchall()
                ]
        return {
            "users": rows,
            "total_users": len(rows),
            "storage_backend": "postgres",
            "schema": self.database_schema,
        }
