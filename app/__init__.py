
# ============================================================
# APPLICATION FACTORY
# ============================================================
# The factory pattern allows the application to be created
# with different configurations for testing, development,
# and production without changing source code.

import os
from datetime import timezone
from zoneinfo import ZoneInfo

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# ============================================================
# EXTENSION INSTANCES
# ============================================================
# Extensions are created here without binding to an app.
# They are attached to the app inside create_app().

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_name=None):
    """
    Create and configure the Flask application.

    Args:
        config_name (str): One of "development", "production",
            or "default". If None, reads from the FLASK_ENV
            environment variable.

    Returns:
        Flask: The configured application instance.
    """

    # Determine which configuration to use
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "default")

    # Create the Flask instance
    app = Flask(__name__)

    # Load configuration from the appropriate class
    from app.config import config_by_name

    app.config.from_object(
        config_by_name.get(config_name, config_by_name["default"])
    )

    def format_local_datetime(value, format_string):
        """Format a stored UTC timestamp in the configured local timezone."""
        if value is None:
            return ""

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        local_value = value.astimezone(
            ZoneInfo(app.config["DISPLAY_TIMEZONE"])
        )
        return local_value.strftime(format_string)

    app.jinja_env.filters["local_datetime"] = format_local_datetime

    # Normalize PostgreSQL URL if provided by Vercel or Heroku.
    # SQLAlchemy requires the postgresql:// prefix.
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = uri.replace(
            "postgres://", "postgresql://", 1
        )

    # ========================================================
    # BIND EXTENSIONS TO APP
    # ========================================================

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    # Configure login manager behavior
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "error"

    # ========================================================
    # REGISTER BLUEPRINTS
    # ========================================================
    # Blueprints group related routes into separate modules.

    from app.auth import auth_bp
    from app.main import main_bp
    from app.api import api_bp
    from app.exports import exports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(exports_bp)

    # ========================================================
    # USER LOADER
    # ========================================================
    # Flask-Login uses this callback to reload the user object
    # from the session on every request.

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    # ========================================================
    # DATABASE INITIALIZATION
    # ========================================================
    # Create tables that do not yet exist. Safe to call on
    # every startup.

    with app.app_context():
        from app.models import User, Computation, TaxBracket
        from app.tax.graduated import TAX_BRACKETS

        db.create_all()

        if TaxBracket.query.count() == 0:
            for upper, base_tax, rate, threshold in TAX_BRACKETS:
                db.session.add(TaxBracket(
                    tax_year="2023 onwards (TRAIN Law)",
                    over_amount=None if threshold == 0 else threshold,
                    upper_amount=None if upper == float("inf") else upper,
                    base_tax=base_tax,
                    rate=rate,
                    threshold=threshold,
                    is_active=True,
                ))
            db.session.commit()

    return app