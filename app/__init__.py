import os
from flask import Flask
from .db import close_db, init_app

def create_app():
    """Create and configure the Flask application"""
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required")

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
    )
    app.config.from_mapping(
        SECRET_KEY=secret_key,
        DATABASE=os.path.join(app.instance_path, "virtual_clinic.sqlite"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
        SESSION_COOKIE_SAMESITE="Lax",
    )
    os.makedirs(app.instance_path, exist_ok=True)

    from . import routes
    app.register_blueprint(routes.bp)
    app.teardown_appcontext(close_db)
    init_app(app)

    return app
