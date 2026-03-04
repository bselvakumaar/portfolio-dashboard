import base64
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import jwt
import psycopg


class AuthService:
    def __init__(
        self,
        database_url: str,
        database_schema: str,
        jwt_secret: str,
        jwt_algorithm: str,
        jwt_exp_minutes: int,
        superadmin_email: str,
        superadmin_password: str,
    ) -> None:
        self.database_url = self._normalize_database_url(database_url.strip())
        self.database_schema = database_schema.strip() or "stock-dashboard"
        self._qschema = f'"{self.database_schema.replace(chr(34), chr(34) * 2)}"'
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.jwt_exp_minutes = jwt_exp_minutes
        self.superadmin_email = superadmin_email.strip().lower()
        self.superadmin_password = superadmin_password
        if not self.database_url:
            raise ValueError("AuthService requires TRADING_DATABASE_URL / encrypted DB URL")
        self._init_db()
        self._ensure_superadmin()

    def _normalize_database_url(self, url: str) -> str:
        if not url:
            return ""
        single_quoted_pw = re.search(r":'([^']*)'@", url)
        if single_quoted_pw:
            password = quote(single_quoted_pw.group(1), safe="")
            return url.replace(single_quoted_pw.group(0), f":{password}@", 1)
        return url

    def _connect(self):
        return psycopg.connect(self.database_url)

    def _init_db(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self._qschema}")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qschema}.auth_users (
                      id BIGSERIAL PRIMARY KEY,
                      email TEXT UNIQUE NOT NULL,
                      full_name TEXT NOT NULL DEFAULT '',
                      password_hash TEXT NOT NULL,
                      role TEXT NOT NULL DEFAULT 'user',
                      is_active BOOLEAN NOT NULL DEFAULT TRUE,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_auth_users_email
                    ON {self._qschema}.auth_users (email)
                    """
                )
            conn.commit()

    def _hash_password(self, password: str, salt_b64: str | None = None) -> str:
        salt = os.urandom(16) if salt_b64 is None else base64.b64decode(salt_b64.encode("utf-8"))
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return f"pbkdf2_sha256$120000${base64.b64encode(salt).decode('utf-8')}${base64.b64encode(digest).decode('utf-8')}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algo, iterations, salt_b64, hash_b64 = stored_hash.split("$", 3)
            if algo != "pbkdf2_sha256":
                return False
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                base64.b64decode(salt_b64.encode("utf-8")),
                int(iterations),
            )
            return hmac.compare_digest(base64.b64encode(digest).decode("utf-8"), hash_b64)
        except Exception:
            return False

    def _ensure_superadmin(self) -> None:
        if not self.superadmin_email:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id FROM {self._qschema}.auth_users WHERE email = %s",
                    (self.superadmin_email,),
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        f"""
                        UPDATE {self._qschema}.auth_users
                        SET role='superadmin',
                            full_name='Platform Superadmin',
                            password_hash=%s
                        WHERE email=%s
                        """,
                        (self._hash_password(self.superadmin_password), self.superadmin_email),
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO {self._qschema}.auth_users (email, full_name, password_hash, role)
                        VALUES (%s, %s, %s, 'superadmin')
                        """,
                        (
                            self.superadmin_email,
                            "Platform Superadmin",
                            self._hash_password(self.superadmin_password),
                        ),
                    )
            conn.commit()

    def _issue_token(self, user: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user["email"],
            "role": user["role"],
            "full_name": user.get("full_name", ""),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.jwt_exp_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def register_user(self, email: str, password: str, full_name: str = "") -> dict[str, Any]:
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("Valid email is required")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id FROM {self._qschema}.auth_users WHERE email=%s",
                    (normalized_email,),
                )
                if cur.fetchone():
                    raise ValueError("Email already registered")
                cur.execute(
                    f"""
                    INSERT INTO {self._qschema}.auth_users (email, full_name, password_hash, role)
                    VALUES (%s, %s, %s, 'user')
                    """,
                    (
                        normalized_email,
                        full_name.strip(),
                        self._hash_password(password),
                    ),
                )
            conn.commit()
        return self.get_user_by_email(normalized_email)

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT email, full_name, role, is_active, created_at
                    FROM {self._qschema}.auth_users
                    WHERE email = %s
                    """,
                    (email.strip().lower(),),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("User not found")
        return {
            "email": row[0],
            "full_name": row[1] or "",
            "role": row[2],
            "is_active": bool(row[3]),
            "created_at": row[4].isoformat() if row[4] else None,
        }

    def login(self, email: str, password: str) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT email, full_name, role, is_active, password_hash
                    FROM {self._qschema}.auth_users
                    WHERE email = %s
                    """,
                    (normalized_email,),
                )
                row = cur.fetchone()
        if not row:
            raise ValueError("Invalid credentials")
        if not bool(row[3]):
            raise ValueError("User is inactive")
        if not self._verify_password(password, row[4]):
            raise ValueError("Invalid credentials")
        user = {"email": row[0], "full_name": row[1] or "", "role": row[2]}
        return {"access_token": self._issue_token(user), "token_type": "bearer", "user": user}

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid or expired token") from exc
        email = str(payload.get("sub", "")).strip().lower()
        if not email:
            raise ValueError("Invalid token payload")
        user = self.get_user_by_email(email)
        return user
