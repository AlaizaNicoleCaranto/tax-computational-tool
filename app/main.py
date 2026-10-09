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

import math

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from flask_login import current_user, login_required

from app import db
from app.models import Computation, TaxBracket

# Blueprint definition with an empty URL prefix so that the
# dashboard lives at the site root.
main_bp = Blueprint("main", __name__)


def is_tax_admin():
    """Return whether the signed-in user may edit tax rules."""
    admin_email = current_app.config.get("ADMIN_EMAIL", "").strip().lower()
    if not admin_email:
        # Default: all authenticated users can view and edit the tax table
        return current_user.is_authenticated
    return (
        current_user.is_authenticated
        and current_user.email.lower() == admin_email
    )


@main_bp.app_context_processor
def inject_admin_status():
    return dict(is_tax_admin=is_tax_admin())


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
    tax_brackets = (
        TaxBracket.query
        .filter_by(is_active=True)
        .order_by(TaxBracket.threshold.asc())
        .all()
    )
    return render_template("index.html", tax_brackets=tax_brackets)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Show a quick summary and recent computations."""
    computations = (
        Computation.query
        .filter_by(user_id=current_user.id)
        .order_by(Computation.created_at.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        computations=computations[:5],
        computation_count=len(computations),
        lowest_tax=min(
            (computation.best_tax or 0 for computation in computations),
            default=0,
        ),
    )


@main_bp.route("/tax-table", methods=["GET", "POST"])
@login_required
def tax_table():
    """Display and update the active graduated tax table."""
    is_admin = is_tax_admin()

    if request.method == "POST":
        if not is_admin:
            abort(403)
        action = request.form.get("action", "save")

        # Action 1: Reset to official BIR TRAIN Law defaults from image
        if action == "reset_defaults":
            from app.tax.graduated import TAX_BRACKETS

            TaxBracket.query.delete()
            for upper, base_tax, rate, threshold in TAX_BRACKETS:
                db.session.add(
                    TaxBracket(
                        tax_year="2023 onwards (TRAIN Law)",
                        over_amount=None if threshold == 0 else threshold,
                        upper_amount=None if upper == float("inf") else upper,
                        base_tax=base_tax,
                        rate=rate,
                        threshold=threshold,
                        is_active=True,
                    )
                )
            db.session.commit()
            flash(
                "Tax table reset to official BIR TRAIN Law defaults.",
                "success",
            )
            return redirect(url_for("main.tax_table"))

        tax_year = (
            request.form.get("tax_year", "").strip()
            or "2023 onwards (TRAIN Law)"
        )

        thresholds = request.form.getlist("threshold[]")
        upper_amounts = request.form.getlist("upper_amount[]")
        base_taxes = request.form.getlist("base_tax[]")
        rates = request.form.getlist("rate[]")

        # Support dynamic multi-row form submission
        if thresholds:
            try:
                new_brackets = []
                for i in range(len(thresholds)):
                    thresh_str = str(thresholds[i]).replace(",", "").strip()
                    thresh = float(thresh_str) if thresh_str else 0.0

                    upper_str = (
                        str(upper_amounts[i]).replace(",", "").strip()
                        if i < len(upper_amounts)
                        else ""
                    )
                    upper = float(upper_str) if upper_str else None

                    btax_str = (
                        str(base_taxes[i]).replace(",", "").strip()
                        if i < len(base_taxes)
                        else "0"
                    )
                    btax = float(btax_str) if btax_str else 0.0

                    rate_str = (
                        str(rates[i]).replace(",", "").strip()
                        if i < len(rates)
                        else "0"
                    )
                    r = (float(rate_str) / 100) if rate_str else 0.0

                    if (
                        not all(math.isfinite(value) for value in (
                            thresh, btax, r,
                        ))
                        or thresh < 0
                        or btax < 0
                        or r < 0
                        or r > 1
                    ):
                        raise ValueError(
                            "Amounts must be finite and non-negative, and rates must be between 0 and 100%."
                        )
                    if upper is not None and (
                        not math.isfinite(upper) or upper <= thresh
                    ):
                        raise ValueError(
                            f"Bracket {i+1}: 'But Not Over' ({upper:,.2f}) must be greater than 'Over' ({thresh:,.2f})."
                        )

                    new_brackets.append(
                        {
                            "tax_year": tax_year,
                            "threshold": thresh,
                            "upper_amount": upper,
                            "base_tax": btax,
                            "rate": r,
                            "over_amount": thresh or None,
                            "is_active": True,
                        }
                    )

                if not new_brackets:
                    raise ValueError("At least one tax bracket is required.")

                new_brackets.sort(key=lambda b: b["threshold"])

                if new_brackets[0]["threshold"] != 0:
                    raise ValueError(
                        "The first tax bracket must start at 0."
                    )

                for index in range(1, len(new_brackets)):
                    previous = new_brackets[index - 1]
                    current = new_brackets[index]
                    if previous["upper_amount"] is None:
                        raise ValueError(
                            f"Bracket {index} must have an upper limit before the next bracket."
                        )
                    if not math.isclose(
                        previous["upper_amount"],
                        current["threshold"],
                        rel_tol=0.0,
                        abs_tol=1e-9,
                    ):
                        raise ValueError(
                            "Tax brackets must be continuous: each bracket's "
                            "upper limit must equal the next bracket's threshold."
                        )

                TaxBracket.query.delete()
                for b_data in new_brackets:
                    db.session.add(TaxBracket(**b_data))
                db.session.commit()
                flash(
                    "Tax table updated successfully. New computations will use these values.",
                    "success",
                )
            except ValueError as e:
                db.session.rollback()
                flash(str(e), "error")
            except Exception:
                db.session.rollback()
                flash("Please enter valid numeric tax-table values.", "error")

            return redirect(url_for("main.tax_table"))

        # Fallback to single bracket ID inputs if older form submitted
        brackets = (
            TaxBracket.query.filter_by(is_active=True)
            .order_by(TaxBracket.threshold.asc())
            .all()
        )
        try:
            for bracket in brackets:
                bracket.tax_year = tax_year
                bracket.base_tax = float(
                    request.form[f"base_tax_{bracket.id}"].replace(",", "")
                )
                bracket.rate = (
                    float(request.form[f"rate_{bracket.id}"].replace(",", ""))
                    / 100
                )
                bracket.threshold = float(
                    request.form[f"threshold_{bracket.id}"].replace(",", "")
                )

                upper_value = request.form.get(
                    f"upper_amount_{bracket.id}", ""
                ).replace(",", "").strip()
                bracket.upper_amount = (
                    float(upper_value) if upper_value else None
                )
                bracket.over_amount = bracket.threshold or None

                if (
                    bracket.base_tax < 0
                    or bracket.threshold < 0
                    or bracket.rate < 0
                    or bracket.rate > 1
                    or (
                        bracket.upper_amount is not None
                        and bracket.upper_amount <= bracket.threshold
                    )
                ):
                    raise ValueError

            db.session.commit()
            flash(
                "Tax table updated. New computations will use these values.",
                "success",
            )
        except Exception:
            db.session.rollback()
            flash("Please enter valid, ascending tax-table values.", "error")

        return redirect(url_for("main.tax_table"))

    brackets = (
        TaxBracket.query.filter_by(is_active=True)
        .order_by(TaxBracket.threshold.asc())
        .all()
    )
    return render_template(
        "tax_table.html",
        brackets=brackets,
        is_admin=is_admin,
    )



@main_bp.route("/edit/<int:computation_id>")
@login_required
def edit(computation_id):
    """Open an owned computation as a new editable template."""
    computation = Computation.query.filter_by(
        id=computation_id,
        user_id=current_user.id,
    ).first()

    if computation is None:
        abort(404)

    tax_brackets = (
        TaxBracket.query.filter_by(is_active=True)
        .order_by(TaxBracket.threshold.asc())
        .all()
    )

    return render_template(
        "index.html",
        initial_inputs=computation.inputs,
        template_source_id=computation.id,
        tax_brackets=tax_brackets,
    )


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
