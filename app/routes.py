from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from .auth import (
    SESSION_IDLE_LIFETIME_SECONDS,
    add_note_to_db,
    authenticate_user,
    connect_personel_with_patient,
    create_session,
    delete_note_from_db,
    delete_session,
    delete_user_from_database,
    get_all_patients,
    get_all_personel,
    get_allowed_notes,
    get_authored_notes,
    get_my_notes,
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
        username = request.form.get("username", "")
        role = request.form.get("role", "")

        error = register_user(email, password, role, username)
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
    session_token = request.cookies.get("session_token")
    notes = get_my_notes(session_token)
    return render_template("patient_panel.html", notes=notes)

@bp.route("/doctor")
@role_required(get_current_user, "DOCTOR")
def doctor_panel():
    """doctor panel"""
    session_token = request.cookies.get("session_token")
    patients = get_all_patients(session_token)
    allowed_notes = get_allowed_notes(session_token)
    authored_notes = get_authored_notes(session_token)
    return render_template("doctor_panel.html", patients=patients, allowed_notes=allowed_notes, authored_notes=authored_notes)

@bp.route("/staff")
@role_required(get_current_user, "STAFF")
def staff_panel():
    """staff panel"""
    session_token = request.cookies.get("session_token")
    allowed_notes = get_allowed_notes(session_token)
    return render_template("staff_panel.html", allowed_notes=allowed_notes)

@bp.route("/profile")
def profile():
    "Profile panel"
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    return render_template("profile.html")

@bp.route("/delete_account", methods=("POST",))
def delete_account():
    "Deletion of user account"
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    csrf_error_response = validate_csrf_or_reject()
    if csrf_error_response:
        return csrf_error_response

    session_token = request.cookies.get("session_token")
    if not delete_user_from_database(session_token):
        response = redirect(url_for("main.dashboard"))
        flash("Failed to delete account", "error")
        return response
    delete_session(session_token)

    response = redirect(url_for("main.login"))
    response.delete_cookie(
        "session_token",
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        samesite="Lax",
    )
    flash("Account deleted successfully", "success")
    return response

@bp.route("/add_note/<int:patient_id>", methods=("GET", "POST"))
@role_required(get_current_user, "DOCTOR")
def add_note(patient_id):
    "Adding note for patient"

    if request.method == "POST":
        csrf_error_response = validate_csrf_or_reject()
        if csrf_error_response:
            return csrf_error_response

        note = request.form.get("note", ".")

        session_token = request.cookies.get("session_token")

        if not add_note_to_db(session_token, patient_id, note):
            flash("Failed adding note", "error")
            return redirect(url_for("main.dashboard"))

        flash("Note Added", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("patient_note_form.html", patient_id=patient_id)


@bp.route("/delete_note/<int:note_id>", methods=("POST",))
@role_required(get_current_user, "DOCTOR")
def delete_note(note_id):
    "Adding note for patient"

    csrf_error_response = validate_csrf_or_reject()
    if csrf_error_response:
        return csrf_error_response
    delete_note_from_db(note_id)
    return redirect(url_for("main.doctor_panel"))

@bp.route("/add_personel/<int:patient_id>")
@role_required(get_current_user, "DOCTOR")
def add_personel_list(patient_id):
    """Render List of Personel to add to note"""
    session_token = request.cookies.get("session_token")
    personel = get_all_personel(session_token)
    return render_template("add_allowed.html", patient_id=patient_id, personel=personel)

@bp.route("/add_personel/<int:patient_id>/<int:user_id>", methods=("POST",))
@role_required(get_current_user, "DOCTOR")
def add_personel(patient_id, user_id):
    """Add personel to note"""
    csrf_error_response = validate_csrf_or_reject()
    if csrf_error_response:
        return csrf_error_response
    connect_personel_with_patient(user_id, patient_id)

    flash("Personel Added", "success")
    return redirect(url_for("main.dashboard"))