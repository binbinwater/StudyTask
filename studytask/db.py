import sqlite3

import click
from flask import current_app, g


def get_db():
    """Open one SQLite connection per application context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=10,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    """Create missing tables and indexes without touching existing data."""
    database = get_db()
    with current_app.open_resource("schema.sql") as schema_file:
        database.executescript(schema_file.read().decode("utf-8"))
    database.commit()


@click.command("init-db")
def init_db_command():
    """Create the database schema (safe to run repeatedly)."""
    init_db()
    click.echo("数据库已初始化。")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)