from flask import Blueprint, flash, redirect, render_template, request, url_for

from .auth import register_user

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    """root URL to the login page"""
    return redirect(url_for("main.login"))

@bp.route("/login")
def login():
    """login page"""
    return render_template("login.html")

@bp.route("/register", methods=("GET", "POST"))
def register():
    """registration page"""
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
    return render_template("dashboard.html")

@bp.route("/patient")
def patient_panel():
    """patient panel"""
    return render_template("patient_panel.html")

@bp.route("/doctor")
def doctor_panel():
    """doctor panel"""
    return render_template("doctor_panel.html")

@bp.route("/staff")
def staff_panel():
    """staff panel"""
    return render_template("staff_panel.html")
