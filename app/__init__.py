import os
from flask import Flask
from .db import close_db, init_app

def create_app():
    """Create and configure the Flask application"""
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
    )
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "virtual_clinic.sqlite"),
    )
    os.makedirs(app.instance_path, exist_ok=True)

    from . import routes
    app.register_blueprint(routes.bp)
    app.teardown_appcontext(close_db)
    init_app(app)

    return app
