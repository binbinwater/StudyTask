import os
from datetime import date, datetime

from flask import Flask

from . import db


def create_app(test_config=None):
    """Create and configure the StudyTask application."""
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "studytask.sqlite3"),
        SECRET_KEY=os.environ.get("SECRET_KEY", "studytask-local-development"),
        # Tests may inject a fixed date so reminder/statistics assertions are stable.
        TODAY_OVERRIDE=None,
    )

    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)

    # Creating the schema on startup is idempotent and lets a fresh checkout run
    # without a separate migration tool. Existing task rows are never removed.
    with app.app_context():
        db.init_db()

    return app


def current_date():
    """Return the configured reference date, or the server's local date."""
    from flask import current_app

    override = current_app.config.get("TODAY_OVERRIDE")
    if override is None:
        return date.today()
    if isinstance(override, datetime):
        return override.date()
    if isinstance(override, date):
        return override
    return date.fromisoformat(str(override))