import hashlib
import hmac
import sqlite3
import secrets
from datetime import datetime, timezone

from .db import get_db

ALLOWED_ROLES = {"PATIENT", "DOCTOR", "STAFF"}
PASSWORD_HASH_ITERATIONS = 600_000

def generate_salt():
    """Generate a random password salt"""
    return secrets.token_hex(16)

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
