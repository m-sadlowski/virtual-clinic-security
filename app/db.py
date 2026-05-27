import sqlite3
import click
from flask import current_app, g

def get_db():
    """Return the database connection for the current context"""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    """Close the database connection"""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create database tables"""
    db = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        db.executescript(schema_file.read().decode("utf-8"))

# opakowanie jako komenda CLI -> flask init-db w cmd
@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the database")

def init_app(app):
    """Register database commands on the Flask app"""
    app.cli.add_command(init_db_command)
