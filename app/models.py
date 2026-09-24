# ============================================================
# DATABASE MODELS
# ============================================================
# Defines the persistent entities for the application. Each
# class maps to a table in the database. Models are kept
# separate from route logic so that they can be imported and
# reused without pulling in the entire application.

from datetime import datetime

from flask_login import UserMixin

# Import the shared extension instance. The actual binding to
# the Flask app happens in app/__init__.py.
from app import db


class User(UserMixin, db.Model):
    """
    Registered taxpayer account.

    Inherits from UserMixin to provide the default Flask-Login
    interface (is_authenticated, is_active, get_id, and so on).

    A user owns zero or more computations. Deleting a user
    cascades to their computations.
    """

    __tablename__ = "users"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Login identifier. Must be unique across all users.
    # Indexed because it is queried on every login attempt.
    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    # Display name shown in the interface and in exports.
    full_name = db.Column(db.String(120), nullable=False)

    # Bcrypt hash of the user's password. Plain passwords are
    # never stored.
    password_hash = db.Column(db.String(255), nullable=False)

    # Account creation timestamp.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to computations. The cascade ensures that
    # deleting a user also deletes all of their saved
    # computations, preventing orphan rows.
    computations = db.relationship(
        "Computation",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        """Developer friendly representation for debugging."""
        return f"<User id={self.id} email={self.email}>"

    def to_dict(self):
        """
        Serialize the user to a dictionary.

        The password hash is intentionally excluded from the
        output so that it can never leak through a JSON
        response.
        """
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
        }


class Computation(db.Model):
    """
    One saved tax computation.

    Raw inputs and computed results are stored as JSON so that
    the schema stays stable even if the frontend adds or
    renames fields. This avoids frequent database migrations
    during the research phase.

    Aggregated columns (taxpayer_type, best_scheme, best_tax)
    are duplicated out of the JSON for easy querying and
    reporting.
    """

    __tablename__ = "computations"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Owner of this computation.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Taxpayer classification: "pure" or "mixed".
    taxpayer_type = db.Column(db.String(20), nullable=False)

    # Raw inputs exactly as submitted by the frontend.
    inputs = db.Column(db.JSON, nullable=False)

    # Computed results for all three schemes.
    results = db.Column(db.JSON, nullable=False)

    # Name of the scheme with the lowest total tax.
    best_scheme = db.Column(db.String(160))

    # Total tax of the best scheme. Stored separately so that
    # reports can sort and filter without parsing JSON.
    best_tax = db.Column(db.Float, default=0)

    # Timestamp for when the computation was saved. Indexed
    # because history views sort by this column.
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        index=True,
    )

    def __repr__(self):
        """Developer friendly representation for debugging."""
        return (
            f"<Computation id={self.id} "
            f"user={self.user_id} "
            f"best={self.best_scheme}>"
        )

    def to_dict(self):
        """
        Serialize the computation to a dictionary.

        Suitable for JSON responses and for CSV/PDF exports
        that need access to the underlying data.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "taxpayer_type": self.taxpayer_type,
            "inputs": self.inputs,
            "results": self.results,
            "best_scheme": self.best_scheme,
            "best_tax": self.best_tax,
            "created_at": self.created_at.isoformat(),
        }