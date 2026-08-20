"""
Security helpers — password hashing and JWT creation/verification.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# ── Secret key ────────────────────────────────────────────────────────────────
_DEFAULT_SECRET = "change-me-in-production-supersecret-key"
# Prefer a real environment variable (e.g. the Render dashboard); fall back to
# the value loaded from .env via Settings; finally the placeholder default.
JWT_SECRET      = os.getenv("JWT_SECRET") or _settings.jwt_secret or _DEFAULT_SECRET
JWT_ALGORITHM   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(_settings.access_token_expire_minutes))
)  # default 8 hours

# Fail-closed: never run in production on the default/placeholder secret.
# A known secret means anyone can forge admin tokens, so we refuse to start.
if JWT_SECRET == _DEFAULT_SECRET and _settings.app_env == "production":
    raise RuntimeError(
        "SECURITY: JWT_SECRET is missing or left at the default placeholder while "
        "APP_ENV=production. Set a strong random JWT_SECRET (e.g. "
        "`python -c \"import secrets; print(secrets.token_hex(32))\"`) before starting."
    )

# ── Password hashing (bcrypt direct — avoids passlib/bcrypt version conflicts) ─
# rounds=10 (~100ms) vs default 12 (~400ms) — still secure, 4x faster on constrained CPU.
_BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


get_password_hash = hash_password


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id:  int,
    username: str,
    role:     str,
    allowed_pages: list | None = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub":      str(user_id),
        "username": username,
        "role":     role,
        "pages":    allowed_pages,   # None = all pages; list = restricted
        "exp":      expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Return payload dict or None if token is invalid/expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
