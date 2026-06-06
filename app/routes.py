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
        password = request.form.get("password", "")
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
