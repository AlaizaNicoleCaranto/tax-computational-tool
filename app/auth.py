# ============================================================
# AUTHENTICATION ROUTES
# ============================================================
# Handles user registration, login, and logout. All routes
# are grouped under the "auth" blueprint so that they can be
# registered with a single call in the app factory.

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

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
        return redirect(url_for("main.index"))

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

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

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
        return redirect(url_for("main.index"))

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
            return redirect(url_for("main.index"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    # GET request: render the empty form.
    return render_template("login.html")


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