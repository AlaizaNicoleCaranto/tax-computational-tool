# ============================================================
# MAIN ROUTES
# ============================================================
# Handles the primary user facing pages that require an
# authenticated session:
#
#     /                dashboard with the calculator
#     /history         list of past computations
#     /view/<id>       detail view of one computation
#     /delete/<id>     delete one computation
#
# All routes here are protected by @login_required.

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    url_for,
)

from flask_login import current_user, login_required

from app import db
from app.models import Computation

# Blueprint definition with an empty URL prefix so that the
# dashboard lives at the site root.
main_bp = Blueprint("main", __name__)


# ============================================================
# DASHBOARD
# ============================================================


@main_bp.route("/")
@login_required
def index():
    """
    Render the main calculator page.

    The page itself is a form. All computation happens through
    the /api/calculate endpoint so that this route stays a
    simple render.
    """
    return render_template("index.html")


# ============================================================
# HISTORY
# ============================================================


@main_bp.route("/history")
@login_required
def history():
    """
    Render the list of computations for the current user.

    Results are ordered newest first so that the most recent
    computation appears at the top.
    """
    computations = (
        Computation.query
        .filter_by(user_id=current_user.id)
        .order_by(Computation.created_at.desc())
        .all()
    )

    return render_template("history.html", computations=computations)


# ============================================================
# VIEW ONE COMPUTATION
# ============================================================


@main_bp.route("/view/<int:computation_id>")
@login_required
def view(computation_id):
    """
    Render the detail view of a single computation.

    The query filters by user_id in addition to the primary
    key so that one user cannot view another user's records
    by guessing the URL.
    """
    computation = Computation.query.filter_by(
        id=computation_id,
        user_id=current_user.id,
    ).first()

    if computation is None:
        # Return 404 rather than 403 so that the existence of
        # another user's record is not revealed.
        abort(404)

    return render_template("view.html", computation=computation)


# ============================================================
# DELETE ONE COMPUTATION
# ============================================================


@main_bp.route("/delete/<int:computation_id>", methods=["POST"])
@login_required
def delete(computation_id):
    """
    Delete a saved computation owned by the current user.

    Only POST is accepted so that a simple link click cannot
    trigger deletion. The detail view renders a small form
    with a confirmation prompt.
    """
    computation = Computation.query.filter_by(
        id=computation_id,
        user_id=current_user.id,
    ).first()

    if computation is None:
        abort(404)

    db.session.delete(computation)
    db.session.commit()

    flash("Computation deleted.", "success")
    return redirect(url_for("main.history"))