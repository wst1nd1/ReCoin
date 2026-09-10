"""Пользователи и вход.

Хранилище – SQLite рядом с проектом. Пароли лежат только в виде
pbkdf2-хеша с индивидуальной солью; исходный пароль нигде не сохраняется
и в логи не попадает.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "recoin.db"

SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # месяц
PBKDF2_ROUNDS = 200_000
MIN_PASSWORD_LENGTH = 8

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str

    @property
    def initials(self) -> str:
        parts = [p for p in self.name.split() if p]
        if not parts:
            return self.email[:1].upper()
        return "".join(p[0].upper() for p in parts[:2])


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                created_at    REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
            """
        )


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds)
    )
    # compare_digest – чтобы время сравнения не зависело от совпавшего префикса.
    return secrets.compare_digest(digest.hex(), digest_hex)


def _row_to_user(row: sqlite3.Row) -> User:
    return User(id=row["id"], email=row["email"], name=row["name"] or row["email"].split("@")[0])


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def register(email: str, password: str, name: str = "") -> User:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise AuthError("Проверьте адрес почты – он выглядит неправильно.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов.")

    with _connect() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            raise AuthError("Такая почта уже зарегистрирована. Войдите вместо регистрации.")
        cursor = conn.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email, (name or "").strip(), _hash_password(password), time.time()),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_user(row)


def authenticate(email: str, password: str) -> User:
    email = normalize_email(email)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    # Один и тот же текст на «нет такого пользователя» и «неверный пароль»,
    # чтобы по ответу нельзя было перебирать существующие адреса.
    if row is None or not _password_matches(password, row["password_hash"]):
        raise AuthError("Неверная почта или пароль.")
    return _row_to_user(row)


def start_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now, now + SESSION_TTL_SECONDS),
        )
    return token


def user_for_token(token: str | None) -> User | None:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT users.* FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, time.time()),
        ).fetchone()
    return _row_to_user(row) if row else None


def end_session(token: str | None) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
