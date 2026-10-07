# ============================================================
# AUTHENTICATION ROUTES
# ============================================================
# Handles user registration, login, and logout. All routes
# are grouped under the "auth" blueprint so that they can be
# registered with a single call in the app factory.

import hashlib

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import OperationalError

from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

# Import the shared extensions and models. The extensions are
# bound to the app in the factory, but they can still be used
# at import time for querying.
from app import bcrypt, db
from app.models import User

# Blueprint definition. URL prefix is empty because the
# authentication pages live at the top level ("/login",
# "/register", "/logout").
auth_bp = Blueprint("auth", __name__)


def _reset_serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="tax-tool-password-reset",
    )


def _password_reset_token(user):
    return _reset_serializer().dumps({
        "user_id": user.id,
        # A reset token becomes invalid after the password is changed.
        "password_marker": hashlib.sha256(
            user.password_hash.encode("utf-8")
        ).hexdigest(),
    })


def _user_from_reset_token(token):
    try:
        payload = _reset_serializer().loads(
            token,
            max_age=current_app.config.get("PASSWORD_RESET_MAX_AGE", 3600),
        )
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None

    try:
        user = db.session.get(User, payload.get("user_id"))
    except OperationalError:
        # Recover from a newly-created/empty SQLite file if the process was
        # started before the database schema was initialized.
        db.session.rollback()
        db.create_all()
        user = db.session.get(User, payload.get("user_id"))
    if not user:
        return None

    marker = hashlib.sha256(user.password_hash.encode("utf-8")).hexdigest()
    return user if payload.get("password_marker") == marker else None


# ============================================================
# REGISTRATION
# ============================================================


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Display the registration form and handle submission.

    On GET, renders the form. On POST, validates the input,
    creates a new user, and redirects to the login page.

    Validation rules:
        - All fields are required.
        - Email must not already be registered.
        - Password must be at least 6 characters.
        - Password and confirmation must match.
    """
    # Redirect already logged in users to the dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        # Normalize the input. Email is lowercased to avoid
        # duplicate accounts that differ only in case.
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Validate required fields.
        if not email or not full_name or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("auth.register"))

        # Validate password length.
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("auth.register"))

        # Validate password confirmation.
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("auth.register"))

        # Validate email uniqueness.
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash(
                "That email is already registered. Please log in.",
                "error",
            )
            return redirect(url_for("auth.login"))

        # Create the user with a hashed password.
        user = User(
            email=email,
            full_name=full_name,
            password_hash=bcrypt.generate_password_hash(
                password
            ).decode("utf-8"),
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Account created successfully. Welcome, {user.full_name}!", "success")
        return redirect(url_for("main.dashboard"))

    # GET request: render the empty form.
    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Display the login form and handle submission.

    On success, the user session is created and the user is
    redirected to the dashboard. On failure, a generic error
    message is shown so that valid emails are not revealed.
    """
    # Redirect already logged in users to the dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Look up the user by email.
        user = User.query.filter_by(email=email).first()

        # Verify the password hash. The same generic error is
        # shown whether the email or the password is wrong, so
        # that attackers cannot enumerate registered emails.
        if user and bcrypt.check_password_hash(
            user.password_hash, password
        ):
            login_user(user)
            flash(f"Welcome back, {user.full_name}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and next_page != "/" and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    # GET request: render the empty form.
    return render_template("login.html")


# ============================================================
# PASSWORD RESET
# ============================================================


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Start a password reset without revealing whether an email exists."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if email:
            try:
                user = User.query.filter_by(email=email).first()
            except OperationalError:
                db.session.rollback()
                db.create_all()
                user = User.query.filter_by(email=email).first()
        else:
            user = None

        if user:
            token = _password_reset_token(user)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            current_app.logger.info("Password reset requested for %s", email)

            # There is no mail provider configured in this project yet. Keep
            # the link visible for local development and log it for deployment
            # integration, without exposing account existence to the requester.
            if current_app.debug:
                flash(f"Development reset link: {reset_url}", "success")

        flash(
            "If an account exists for that email, password-reset instructions have been sent.",
            "success",
        )
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Validate a time-limited reset token and set a new password."""
    user = _user_from_reset_token(token)
    if not user:
        flash("That password-reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("reset_password.html", token=token)
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html", token=token)

        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()
        flash("Your password has been reset. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


# ============================================================
# LOGOUT
# ============================================================


@auth_bp.route("/logout")
@login_required
def logout():
    """
    End the current session and redirect to the login page.
    """
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
