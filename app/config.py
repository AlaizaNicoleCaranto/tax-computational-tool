# ============================================================
# APPLICATION CONFIGURATION
# ============================================================
# Centralizes all configuration values so that environment
# specific settings are defined in one place. The app factory
# imports these classes when creating the Flask instance.

import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present.
# This allows local development to override defaults without
# modifying source code.
load_dotenv()

# Resolve the local SQLite database from the project location rather
# than from the process working directory. This prevents different
# launchers (Flask CLI, an IDE, or run.py) from opening different empty
# tax_tool.db files.
DEFAULT_SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "instance",
    "tax_tool.db",
)
DEFAULT_SQLITE_URI = f"sqlite:///{DEFAULT_SQLITE_PATH}"


class Config:
    """
    Base configuration shared by all environments.

    Values that may change between local development and
    production deployment are read from environment variables
    with sensible defaults.
    """

    # Secret key used to sign session cookies and CSRF tokens.
    # Must be replaced with a strong random value in production.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()

    # SMTP settings used by password-reset emails. Configure these in the
    # deployment environment; no credentials are stored in source control.
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_FROM = os.getenv("MAIL_FROM", "").strip()

    # Timezone used when displaying stored UTC timestamps to users.
    DISPLAY_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Singapore")

    # Database connection string. Defaults to SQLite for local
    # development. In production, this should be set to a
    # PostgreSQL URL via the DATABASE_URL environment variable.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", DEFAULT_SQLITE_URI
    )

    # Disable SQLAlchemy modification tracking to reduce memory
    # usage. Not needed unless using Flask-SQLAlchemy events.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Automatically remove database sessions at the end of each
    # request to avoid stale connections.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # Session cookie security flags. Enabled in production to
    # require HTTPS. Kept False locally so HTTP works.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    """
    Configuration for local development.

    Enables debug mode and uses a local SQLite file.
    """

    DEBUG = True

    # Local SQLite database stored inside the instance folder.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", DEFAULT_SQLITE_URI
    )


class ProductionConfig(Config):
    """
    Configuration for production deployment.

    Requires DATABASE_URL to be set to a PostgreSQL connection
    string. Secure cookies are enforced.
    """

    DEBUG = False

    # Force secure cookies in production. Vercel serves over
    # HTTPS, so this is safe.
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """
    Configuration for automated tests.

    Uses an in-memory SQLite database so test runs never touch
    or wipe the development database on disk.
    """

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"


# Mapping used by the app factory to select a configuration
# class based on the FLASK_ENV environment variable.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
