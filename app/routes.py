from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from .auth import (
    SESSION_IDLE_LIFETIME_SECONDS,
    authenticate_user,
    create_session,
    delete_session,
    get_user_by_session_token,
    register_user,
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

@bp.app_context_processor
def inject_current_user():
    """Make the current user available in templates"""
    return {"current_user": get_current_user()}

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
            samesite="Lax",
        )
    elif getattr(g, "clear_session_cookie", False):
        response.delete_cookie("session_token")

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
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user, error = authenticate_user(email, password)
        if error:
            flash(error, "danger")
            return render_template("login.html", email=email)

        session_token = create_session(user["id"])
        response = redirect(url_for("main.dashboard"))
        response.set_cookie(
            "session_token",
            session_token,
            httponly=True,
            max_age=SESSION_IDLE_LIFETIME_SECONDS,
            samesite="Lax",
        )
        flash("Logged in successfully", "success")
        return response

    return render_template("login.html")

@bp.route("/logout")
def logout():
    """log out the current user"""
    session_token = request.cookies.get("session_token")
    delete_session(session_token)

    response = redirect(url_for("main.login"))
    response.delete_cookie("session_token")
    flash("Logged out successfully", "success")
    return response

@bp.route("/register", methods=("GET", "POST"))
def register():
    """registration page"""
    if get_current_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
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

    return render_template("dashboard.html")

@bp.route("/patient")
def patient_panel():
    """patient panel"""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    return render_template("patient_panel.html")

@bp.route("/doctor")
def doctor_panel():
    """doctor panel"""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    return render_template("doctor_panel.html")

@bp.route("/staff")
def staff_panel():
    """staff panel"""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    return render_template("staff_panel.html")
