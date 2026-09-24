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

    # Database connection string. Defaults to SQLite for local
    # development. In production, this should be set to a
    # PostgreSQL URL via the DATABASE_URL environment variable.
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///tax_tool.db"
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
        "DATABASE_URL", "sqlite:///tax_tool.db"
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


# Mapping used by the app factory to select a configuration
# class based on the FLASK_ENV environment variable.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}