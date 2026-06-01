import hashlib
import hmac
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone

from .db import get_db

ALLOWED_ROLES = {"PATIENT", "DOCTOR", "STAFF"}
PASSWORD_HASH_ITERATIONS = 600_000
SESSION_IDLE_LIFETIME_MINUTES = 3
SESSION_IDLE_LIFETIME_SECONDS = SESSION_IDLE_LIFETIME_MINUTES * 60
SESSION_ABSOLUTE_LIFETIME_HOURS = 1

def generate_salt():
    """Generate a random password salt"""
    return secrets.token_hex(16)

def generate_session_token():
    """Generate a random session token"""
    return secrets.token_urlsafe(32)

def hash_password(password, salt):
    """Hash a password with PBKDF2-HMAC using salt"""
    password_bytes = password.encode("utf-8")
    salt_bytes = bytes.fromhex(salt)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt_bytes,
        PASSWORD_HASH_ITERATIONS,
    )
    return password_hash.hex()

def verify_password(password, salt, expected_hash):
    """Return True when the password matches the stored hash"""
    password_hash = hash_password(password, salt)
    return hmac.compare_digest(password_hash, expected_hash)

def is_valid_role(role):
    """Return True when the role is supported by the application"""
    return role in ALLOWED_ROLES

def register_user(email, password, role):
    """Register a new user and return an error when it fails"""
    email = email.strip().lower() if email else ""
    password = password or ""
    role = role or ""

    if not email or not password or not role:
        return "All fields are required"

    if not is_valid_role(role):
        return "Selected role is not valid"

    salt = generate_salt()
    password_hash = hash_password(password, salt)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        db = get_db()
        db.execute(
            """
            INSERT INTO users (email, password_hash, password_salt, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, password_hash, salt, role, created_at),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return "A user with this email already exists"

    return None

def authenticate_user(email, password):
    """Return a user when credentials are valid"""
    email = email.strip().lower() if email else ""
    password = password or ""

    if not email or not password:
        return None, "Email and password are required"

    db = get_db()
    user = db.execute(
        """
        SELECT id, email, password_hash, password_salt, role
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if user is None or not verify_password(
        password,
        user["password_salt"],
        user["password_hash"],
    ):
        return None, "Invalid email or password"

    return user, None

def create_session(user_id):
    """Create a database session and return its token"""
    session_token = generate_session_token()
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(minutes=SESSION_IDLE_LIFETIME_MINUTES)

    db = get_db()
    db.execute(
        """
        INSERT INTO sessions (session_token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            session_token,
            user_id,
            created_at.isoformat(),
            expires_at.isoformat(),
        ),
    )
    db.commit()

    return session_token

def delete_expired_sessions():
    """Delete sessions that are past their expiration time"""
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    db.execute(
        """
        DELETE FROM sessions
        WHERE expires_at <= ?
        """,
        (now,),
    )
    db.commit()

def delete_session(session_token):
    """Delete one session by token"""
    if not session_token:
        return

    db = get_db()
    db.execute(
        """
        DELETE FROM sessions
        WHERE session_token = ?
        """,
        (session_token,),
    )
    db.commit()

def get_user_by_session_token(session_token):
    """Return a user and refresh the session when the session token is valid"""
    if not session_token:
        return None

    delete_expired_sessions()

    db = get_db()
    now = datetime.now(timezone.utc)
    session = db.execute(
        """
        SELECT
            sessions.id AS session_id,
            sessions.created_at,
            sessions.expires_at,
            users.id AS user_id,
            users.email,
            users.role
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.session_token = ?
          AND sessions.expires_at > ?
        """,
        (session_token, now.isoformat()),
    ).fetchone()

    if session is None:
        return None

    try:
        created_at = datetime.fromisoformat(session["created_at"])
    except ValueError:
        delete_session(session_token)
        return None

    absolute_expires_at = created_at + timedelta(hours=SESSION_ABSOLUTE_LIFETIME_HOURS)
    if absolute_expires_at <= now:
        delete_session(session_token)
        return None

    refreshed_expires_at = now + timedelta(minutes=SESSION_IDLE_LIFETIME_MINUTES)
    if refreshed_expires_at > absolute_expires_at:
        refreshed_expires_at = absolute_expires_at
    session_cookie_max_age = int((refreshed_expires_at - now).total_seconds())

    db.execute(
        """
        UPDATE sessions
        SET expires_at = ?
        WHERE id = ?
        """,
        (refreshed_expires_at.isoformat(), session["session_id"]),
    )
    db.commit()

    return {
        "id": session["user_id"],
        "email": session["email"],
        "role": session["role"],
        "_session_cookie_max_age": session_cookie_max_age,
    }
