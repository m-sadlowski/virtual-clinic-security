from functools import wraps

from flask import abort, flash, redirect, url_for

ROLE_ENDPOINTS = {
    "PATIENT": "main.patient_panel",
    "DOCTOR": "main.doctor_panel",
    "STAFF": "main.staff_panel",
}

def user_has_role(user, role):
    """Return True when the user has the required role"""
    return bool(user and user.get("role") == role)

def get_role_endpoint(role):
    """Return the panel endpoint assigned to the role"""
    return ROLE_ENDPOINTS.get(role)

def role_required(get_current_user, role):
    """Require authentication and specific role for a route"""
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            current_user = get_current_user()
            if current_user is None:
                flash("Log in to access this page", "danger")
                return redirect(url_for("main.login"))
            if not user_has_role(current_user, role):
                abort(403)
            return view(*args, **kwargs)
        return wrapped_view
    return decorator  

