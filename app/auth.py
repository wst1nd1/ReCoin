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

# Восстановление пароля: код из шести цифр, живёт четверть часа,
# после пяти неверных попыток перестаёт действовать.
RESET_CODE_TTL_SECONDS = 15 * 60
RESET_MAX_ATTEMPTS = 5

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DIGIT_RE = re.compile(r"\d")
_UPPER_RE = re.compile(r"[A-ZА-ЯЁ]")
# Специальным считается любой знак, кроме букв, цифр и пробела.
_SPECIAL_RE = re.compile(r"[^A-Za-zА-Яа-яЁё0-9\s]")


class AuthError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    created_at: float = 0.0
    avatar_version: float = 0.0  # 0 означает, что картинка не загружена

    @property
    def initials(self) -> str:
        parts = [p for p in self.name.split() if p]
        if not parts:
            return self.email[:1].upper()
        return "".join(p[0].upper() for p in parts[:2])

    @property
    def has_avatar(self) -> bool:
        return self.avatar_version > 0


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
            CREATE TABLE IF NOT EXISTS reset_codes (
                email      TEXT PRIMARY KEY,
                code_hash  TEXT NOT NULL,
                expires_at REAL NOT NULL,
                attempts   INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        # Картинка профиля появилась позже, поэтому столбцы добавляются
        # отдельно: у прежних баз их нет.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        for column, definition in (
            ("avatar", "BLOB"),
            ("avatar_type", "TEXT"),
            ("avatar_updated", "REAL"),
        ):
            if column not in existing:
                conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")


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
    keys = row.keys()
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"] or row["email"].split("@")[0],
        created_at=row["created_at"] if "created_at" in keys else 0.0,
        avatar_version=(row["avatar_updated"] or 0.0) if "avatar_updated" in keys else 0.0,
    )


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def password_problems(password: str) -> list[str]:
    """Чего не хватает паролю. Пустой список означает, что пароль подходит."""
    password = password or ""
    missing = []
    if len(password) < MIN_PASSWORD_LENGTH:
        missing.append(f"не менее {MIN_PASSWORD_LENGTH} символов")
    if not _DIGIT_RE.search(password):
        missing.append("цифра")
    if not _UPPER_RE.search(password):
        missing.append("заглавная буква")
    if not _SPECIAL_RE.search(password):
        missing.append("специальный знак")
    return missing


def validate_password(password: str) -> None:
    missing = password_problems(password)
    if missing:
        raise AuthError("Пароль не подходит. Требуется " + ", ".join(missing) + ".")


def register(email: str, password: str, name: str = "") -> User:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise AuthError("Проверьте адрес почты – он выглядит неправильно.")
    validate_password(password)

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


# ---------- восстановление пароля ----------


def create_reset_code(email: str) -> tuple[str, str] | None:
    """Выдать код восстановления. None, если такой почты нет.

    Возвращает пару из кода и имени пользователя. Код существует только
    в этот момент, на диск попадает лишь его хеш.
    """
    email = normalize_email(email)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            return None

        code = f"{secrets.randbelow(1_000_000):06d}"
        conn.execute(
            """
            INSERT INTO reset_codes (email, code_hash, expires_at, attempts)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(email) DO UPDATE SET
                code_hash = excluded.code_hash,
                expires_at = excluded.expires_at,
                attempts = 0
            """,
            (email, _hash_password(code), time.time() + RESET_CODE_TTL_SECONDS),
        )
    return code, _row_to_user(row).name


def reset_password(email: str, code: str, new_password: str) -> User:
    """Сменить пароль по коду из письма."""
    email = normalize_email(email)
    validate_password(new_password)

    with _connect() as conn:
        row = conn.execute("SELECT * FROM reset_codes WHERE email = ?", (email,)).fetchone()
        if row is None:
            raise AuthError("Код не запрашивался. Начните восстановление заново.")
        if row["expires_at"] < time.time():
            conn.execute("DELETE FROM reset_codes WHERE email = ?", (email,))
            raise AuthError("Срок действия кода истёк. Запросите новый.")
        if row["attempts"] >= RESET_MAX_ATTEMPTS:
            conn.execute("DELETE FROM reset_codes WHERE email = ?", (email,))
            raise AuthError("Слишком много попыток. Запросите новый код.")

        if not _password_matches((code or "").strip(), row["code_hash"]):
            conn.execute(
                "UPDATE reset_codes SET attempts = attempts + 1 WHERE email = ?", (email,)
            )
            left = RESET_MAX_ATTEMPTS - row["attempts"] - 1
            if left > 0:
                raise AuthError(f"Неверный код. Осталось попыток: {left}.")
            raise AuthError("Неверный код. Попытки исчерпаны, запросите новый.")

        user_row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user_row is None:
            raise AuthError("Учётная запись не найдена.")

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_row["id"]),
        )
        conn.execute("DELETE FROM reset_codes WHERE email = ?", (email,))
        # Прежние входы закрываются: если доступ к почте был у постороннего,
        # старые сессии не должны пережить смену пароля.
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_row["id"],))

    return _row_to_user(user_row)


# ---------- картинка профиля ----------


def set_avatar(user_id: int, data: bytes, mime: str) -> float:
    """Сохранить картинку профиля. Возвращает отметку времени для адреса."""
    stamp = time.time()
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET avatar = ?, avatar_type = ?, avatar_updated = ? WHERE id = ?",
            (data, mime, stamp, user_id),
        )
    return stamp


def get_avatar(user_id: int) -> tuple[bytes, str] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT avatar, avatar_type FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None or not row["avatar"]:
        return None
    return row["avatar"], row["avatar_type"] or "image/png"


def clear_avatar(user_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET avatar = NULL, avatar_type = NULL, avatar_updated = NULL WHERE id = ?",
            (user_id,),
        )


def user_by_id(user_id: int) -> User | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None
