from enum import nonmember
import string
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from .auth import (
    SESSION_IDLE_LIFETIME_SECONDS,
    authenticate_user,
    create_session,
    delete_session,
    get_user_by_session_token,
    register_user,
)
from .decorators import get_role_endpoint, role_required, user_has_role
from .security import (
    clear_login_attempts,
    generate_csrf_token,
    get_login_throttle_error,
    register_failed_login_attempt,
    validate_csrf_token,
)

bp = Blueprint("main", __name__)

def get_current_user():
    """Return the user connected with the session cookie"""
    if hasattr(g, "current_user"):
        return g.current_user

    session_token = request.cookies.get("session_token")
    g.current_user = get_user_by_session_token(session_token)
    g.current_session_token = session_token
    g.clear_session_cookie = bool(session_token and g.current_user is None)
    return g.current_user

def require_login():
    """Redirect to login when the user is not authenticated"""
    if get_current_user() is None:
        flash("Log in to access this page", "danger")
        return redirect(url_for("main.login"))

    return None


def get_csrf_error_response():
    """Reject a request when the submitted CSRF token is invalid"""
    flash("Invalid CSRF token", "danger")
    return abort(400)


def validate_csrf_or_reject():
    """Validate the submitted CSRF token for POST requests"""
    submitted_token = request.form.get("csrf_token")
    if not validate_csrf_token(submitted_token):
        return get_csrf_error_response()
    return None


def redirect_to_role_panel(user):
    """Redirect the user to the panel assigned to their role"""
    role_endpoint = get_role_endpoint(user["role"])
    if role_endpoint is None:
        abort(403)
    return redirect(url_for(role_endpoint))

def validate_email(email: str) -> str | None:
    """Check if inputed emain is a valid email format"""
    splited = email.split('@')
    if len(splited) < 2:
        return "Emain either doesnt contain domain or local adress"
    if len(splited) != 2:
        return "Email contains multiple \"@\" symbols"
    allowed_characters_local = string.ascii_letters + string.digits + "!#$%&'*+-/=?^_`{|}~"
    allowed_characters_domain = string.ascii_letters + string.digits + "-" + "."
    local_part = splited[0]
    domain_part = splited[1]
    if local_part == '' or domain_part == '':
        return "Either local address or email domain is missing"

    if local_part.startswith('.') or local_part.endswith('.'):
        return "Local adress cannot start or end with comma"
    if ".." in local_part:
        return "Local adress cannot contail multiple commas next to each other"
    if not set(local_part).issubset(allowed_characters_local):
        return "Local adress contains invalid character"
    if len(local_part) > 64:
        return "Local adress too long"
    
    if domain_part.startswith('-') or local_part.endswith('-'):
        return "Domain cannot end or begin with hyphen"
    if not set(domain_part).issubset(allowed_characters_domain):
        return "Domain contains invalid character"
    if len(domain_part) > 256:
        return "Domain is too long"
    subdomain_part_list = domain_part.split('.')
    for sub in subdomain_part_list:
        if sub == '':
            return "Domain includes empty subdomain"
        if len(sub) > 64:
            return "Subdomain too long"
        if len(sub) == 1:
            return "Subdomain is one character long"
    return None
    
def validate_password(password: str) -> str | None:
    """Check if password is a valid password format"""
    special_characters = string.punctuation + string.whitespace
    if len(password) <= 8:
        return "Password should be at least 8 characters long"
    if password.upper() == password or password.lower() == password or set(password).isdisjoint(special_characters):
        return "Password should include upper case, lower case and at least one special character"
    return None

@bp.app_context_processor
def inject_current_user():
    """Make the current user available in templates"""
    current_user = get_current_user()
    return {
        "current_user": current_user,
        "user_has_role": lambda role: user_has_role(current_user, role),
        "csrf_token": generate_csrf_token,
    }

@bp.after_app_request
def refresh_session_cookie(response):
    """Refresh or clear the browser session cookie after session validation"""
    current_user = getattr(g, "current_user", None)
    session_token = getattr(g, "current_session_token", None)

    if current_user is not None and session_token:
        max_age = current_user.get(
            "_session_cookie_max_age",
            SESSION_IDLE_LIFETIME_SECONDS,
        )
        response.set_cookie(
            "session_token",
            session_token,
            httponly=True,
            max_age=max_age,
            secure=current_app.config["SESSION_COOKIE_SECURE"],
            samesite="Lax",
        )
    elif getattr(g, "clear_session_cookie", False):
        response.delete_cookie(
            "session_token",
            secure=current_app.config["SESSION_COOKIE_SECURE"],
            samesite="Lax",
        )

    return response

@bp.route("/")
def index():
    """root URL to the login page"""
    return redirect(url_for("main.login"))

@bp.route("/login", methods=("GET", "POST"))
def login():
    """login page"""
    if get_current_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        csrf_error_response = validate_csrf_or_reject()
        if csrf_error_response:
            return csrf_error_response

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        throttle_key = f"{request.remote_addr or 'unknown'}:{email}"

        throttle_error = get_login_throttle_error(throttle_key)
        if throttle_error:
            flash(throttle_error, "danger")
            return render_template("login.html", email=email), 429

        user, error = authenticate_user(email, password)
        if error:
            register_failed_login_attempt(throttle_key)
            flash(error, "danger")
            return render_template("login.html", email=email)

        clear_login_attempts(throttle_key)
        session_token = create_session(user["id"])
        response = redirect(url_for("main.dashboard"))
        response.set_cookie(
            "session_token",
            session_token,
            httponly=True,
            max_age=SESSION_IDLE_LIFETIME_SECONDS,
            secure=current_app.config["SESSION_COOKIE_SECURE"],
            samesite="Lax",
        )
        flash("Logged in successfully", "success")
        return response
    return render_template("login.html")

@bp.route("/logout", methods=("POST",))
def logout():
    """log out the current user"""
    csrf_error_response = validate_csrf_or_reject()
    if csrf_error_response:
        return csrf_error_response

    session_token = request.cookies.get("session_token")
    delete_session(session_token)

    response = redirect(url_for("main.login"))
    response.delete_cookie(
        "session_token",
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        samesite="Lax",
    )
    flash("Logged out successfully", "success")
    return response

@bp.route("/register", methods=("GET", "POST"))
def register():
    """registration page"""
    if get_current_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        csrf_error_response = validate_csrf_or_reject()
        if csrf_error_response:
            return csrf_error_response

        email = request.form.get("email", "").strip().lower()
        email_validation_error = validate_email(email)
        if email_validation_error:
            flash(email_validation_error, "danger")
            return render_template("login.html", email=email)
        password = request.form.get("password", "")
        password_validation_error = validate_password(password)
        if password_validation_error:
            flash(password_validation_error, "danger")
            return render_template("login.html", email=email)
        role = request.form.get("role", "")

        error = register_user(email, password, role)
        if error:
            flash(error, "danger")
            return render_template("register.html", email=email, selected_role=role)
        flash("Registration successful. You can now log in", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")

@bp.route("/dashboard")
def dashboard():
    """main dashboard"""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    return redirect_to_role_panel(get_current_user())

@bp.route("/patient")
@role_required(get_current_user, "PATIENT")
def patient_panel():
    """patient panel"""
    return render_template("patient_panel.html")

@bp.route("/doctor")
@role_required(get_current_user, "DOCTOR")
def doctor_panel():
    """doctor panel"""
    return render_template("doctor_panel.html")

@bp.route("/staff")
@role_required(get_current_user, "STAFF")
def staff_panel():
    """staff panel"""
    return render_template("staff_panel.html")
