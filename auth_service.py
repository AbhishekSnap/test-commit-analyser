"""
auth_service.py
---------------
Handles user authentication: login, logout, token generation, and session validation.
"""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, field
from typing import Optional


SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "change-me-in-production")
TOKEN_TTL_SECONDS = 3600  # 1 hour


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    roles: list[str] = field(default_factory=list)


@dataclass
class Session:
    token: str
    user_id: str
    created_at: float
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# In-memory stores (replace with DB in production)
_users: dict[str, User] = {}
_sessions: dict[str, Session] = {}


def _hash_password(password: str) -> str:
    """SHA-256 hash of the password salted with SECRET_KEY."""
    return hmac.new(
        SECRET_KEY.encode(),
        password.encode(),
        hashlib.sha256,
    ).hexdigest()


def _generate_token(user_id: str) -> str:
    """Generate a time-based token tied to the user ID."""
    raw = f"{user_id}:{time.time()}:{os.urandom(16).hex()}"
    return hmac.new(
        SECRET_KEY.encode(),
        raw.encode(),
        hashlib.sha256,
    ).hexdigest()


def register(user_id: str, username: str, password: str, roles: list[str] | None = None) -> User:
    """
    Register a new user. Raises ValueError if user_id already exists.
    Passwords are stored as HMAC-SHA256 hashes — never plain text.
    """
    if user_id in _users:
        raise ValueError(f"User '{user_id}' already exists.")

    user = User(
        user_id=user_id,
        username=username,
        password_hash=_hash_password(password),
        roles=roles or [],
    )
    _users[user_id] = user
    return user


def login(user_id: str, password: str) -> Session:
    """
    Authenticate a user and return a new Session with a signed token.
    Raises ValueError on invalid credentials.
    """
    user = _users.get(user_id)
    if not user or user.password_hash != _hash_password(password):
        raise ValueError("Invalid credentials.")

    token = _generate_token(user_id)
    now = time.time()
    session = Session(
        token=token,
        user_id=user_id,
        created_at=now,
        expires_at=now + TOKEN_TTL_SECONDS,
    )
    _sessions[token] = session
    return session


def logout(token: str) -> None:
    """Invalidate a session token. Silent no-op if token not found."""
    _sessions.pop(token, None)


def validate_token(token: str) -> Optional[User]:
    """
    Validate a session token and return the associated User.
    Returns None if the token is missing, expired, or invalid.
    """
    session = _sessions.get(token)
    if not session or session.is_expired():
        _sessions.pop(token, None)
        return None
    return _users.get(session.user_id)


def has_role(token: str, role: str) -> bool:
    """Return True if the token's user has the specified role."""
    user = validate_token(token)
    return user is not None and role in user.roles
