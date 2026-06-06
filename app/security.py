import secrets
from datetime import datetime, timedelta, timezone

from flask import session

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_MINUTES = 15
LOGIN_BLOCK_MINUTES = 15

_login_attempts = {}

def generate_csrf_token():
    """Return the per-session CSRF token - creating when missing"""
    csrf_token = session.get("csrf_token")
    if csrf_token is None:
        csrf_token = secrets.token_urlsafe(32)
        session["csrf_token"] = csrf_token
    return csrf_token

def validate_csrf_token(submitted_token):
    """Return True when submitted CSRF token matches session token"""
    csrf_token = session.get("csrf_token")
    return bool(csrf_token and submitted_token and secrets.compare_digest(csrf_token, submitted_token))


def _get_login_attempt_entry(throttle_key, now):
    entry = _login_attempts.get(throttle_key)
    if entry is None:
        entry = {
            "attempt_count": 0,
            "window_started_at": now,
            "blocked_until": None,
        }
        _login_attempts[throttle_key] = entry
        return entry

    if now - entry["window_started_at"] >= timedelta(minutes=LOGIN_ATTEMPT_WINDOW_MINUTES):
        entry["attempt_count"] = 0
        entry["window_started_at"] = now
        entry["blocked_until"] = None

    if entry["blocked_until"] is not None and entry["blocked_until"] <= now:
        entry["attempt_count"] = 0
        entry["window_started_at"] = now
        entry["blocked_until"] = None

    return entry

def get_login_throttle_error(throttle_key):
    """Return error message when login attempts are temporarily blocked"""
    now = datetime.now(timezone.utc)
    entry = _get_login_attempt_entry(throttle_key, now)
    if entry["blocked_until"] is None:
        return None
    return "Too many login attempts. Try again in 15 minutes"

def register_failed_login_attempt(throttle_key):
    """Record a failed login attempt for throttle key"""
    now = datetime.now(timezone.utc)
    entry = _get_login_attempt_entry(throttle_key, now)
    entry["attempt_count"] += 1
    if entry["attempt_count"] >= LOGIN_ATTEMPT_LIMIT:
        entry["blocked_until"] = now + timedelta(minutes=LOGIN_BLOCK_MINUTES)

def clear_login_attempts(throttle_key):
    """Clear login throttle data after a successful login"""
    _login_attempts.pop(throttle_key, None)
