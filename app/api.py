# ============================================================
# API ROUTES
# ============================================================

from datetime import datetime, timedelta, timezone
import math

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models import Computation
from app.tax import (
    compute_eight_percent,
    compute_itemized,
    compute_osd,
    recommend_scheme,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

DUPLICATE_WINDOW_MINUTES = 5


# ============================================================
# SHARED HELPERS
# ============================================================


def build_results(data):
    """
    Run the three tax schemes and return the result
    dictionary plus the recommendation.
    """
    osd_result = compute_osd(data)
    itemized_result = compute_itemized(data)
    eight_result = compute_eight_percent(data)

    recommendation = recommend_scheme(
        osd_result, itemized_result, eight_result
    )

    results = {
        "osd": osd_result,
        "itemized": itemized_result,
        "eight": eight_result,
        "best_scheme": recommendation["best_scheme"],
        "best_tax": recommendation["best_tax"],
    }

    return results, recommendation


def has_any_input(data):
    """
    Return True if the payload contains at least one non-zero
    numeric value. Used to reject empty submissions.
    """
    numeric_fields = (
        "gross_compensation",
        "non_taxable_compensation",
        "cash_sales",
        "accrual_sales",
        "cash_cost",
        "accrual_cost",
    )

    for field in numeric_fields:
        try:
            if float(data.get(field, 0) or 0) > 0:
                return True
        except (ValueError, TypeError):
            continue

    # Other income list
    items = data.get("other_income", [])
    if isinstance(items, list):
        for item in items:
            try:
                if float(item.get("amount", 0) or 0) > 0:
                    return True
            except (ValueError, TypeError):
                continue

    # Ordinary deductions dict
    items = data.get("ordinary_deductions", {})
    if isinstance(items, dict):
        for value in items.values():
            try:
                if float(value or 0) > 0:
                    return True
            except (ValueError, TypeError):
                continue

    # Special deductions list
    items = data.get("special_deductions", [])
    if isinstance(items, list):
        for item in items:
            try:
                if float(item.get("amount", 0) or 0) > 0:
                    return True
            except (ValueError, TypeError):
                continue

    # NOLCO rows
    items = data.get("nolco", [])
    if isinstance(items, list):
        for row in items:
            for col in ("a", "b", "c", "d"):
                try:
                    if float(row.get(col, 0) or 0) > 0:
                        return True
                except (ValueError, TypeError):
                    continue

    return False


def validate_tax_parameters(data):
    """Reject impossible manual tax parameters before calculation."""
    if not isinstance(data, dict):
        return "Request data must be a JSON object."

    percentage_fields = (
        "osd_percentage",
        "percentage_tax_rate",
        "flat_rate",
        "osd_excess_rate",
        "itemized_excess_rate",
        "compensation_excess_rate",
    )

    for field in percentage_fields:
        if field not in data or data[field] is None or data[field] == "":
            continue
        try:
            value = float(data[field])
        except (TypeError, ValueError):
            return f"{field.replace('_', ' ').title()} must be numeric."
        if not math.isfinite(value) or value < 0 or value > 100:
            return f"{field.replace('_', ' ').title()} must be between 0 and 100."

    if "standard_deduction" in data and data["standard_deduction"] is not None and data["standard_deduction"] != "":
        try:
            value = float(data["standard_deduction"])
            if not math.isfinite(value) or value < 0:
                return "Standard deduction cannot be negative."
        except (TypeError, ValueError):
            return "Standard deduction must be numeric."

    amount_fields = (
        "gross_compensation",
        "non_taxable_compensation",
        "cash_sales",
        "accrual_sales",
        "cash_cost",
        "accrual_cost",
        "osd_basic_tax",
        "osd_excess_amount",
        "itemized_basic_tax",
        "itemized_excess_amount",
        "compensation_basic_tax",
        "compensation_excess_amount",
    )

    for field in amount_fields:
        if field not in data or data[field] is None or data[field] == "":
            continue
        try:
            value = float(str(data[field]).replace(",", ""))
        except (TypeError, ValueError):
            return f"{field.replace('_', ' ').title()} must be numeric."
        if not math.isfinite(value) or value < 0:
            return f"{field.replace('_', ' ').title()} cannot be negative."

    for field in ("other_income", "special_deductions", "nolco"):
        if field in data and not isinstance(data[field], list):
            return f"{field.replace('_', ' ').title()} must be a list."

    for field in ("other_income", "special_deductions"):
        for item in data.get(field, []):
            if not isinstance(item, dict):
                return f"Entries in {field.replace('_', ' ')} must be objects."
            try:
                value = float(str(item.get("amount", 0)).replace(",", ""))
            except (TypeError, ValueError):
                return f"Amounts in {field.replace('_', ' ')} must be numeric."
            if not math.isfinite(value) or value < 0:
                return f"Amounts in {field.replace('_', ' ')} cannot be negative."

    ordinary = data.get("ordinary_deductions", {})
    if not isinstance(ordinary, dict):
        return "Ordinary deductions must be an object."
    for value in ordinary.values():
        try:
            numeric_value = float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return "Ordinary deduction amounts must be numeric."
        if not math.isfinite(numeric_value) or numeric_value < 0:
            return "Ordinary deduction amounts cannot be negative."

    for row in data.get("nolco", []):
        if not isinstance(row, dict):
            return "NOLCO entries must be objects."
        for column in ("a", "b", "c", "d"):
            try:
                numeric_value = float(
                    str(row.get(column, 0)).replace(",", "")
                )
            except (TypeError, ValueError):
                return "NOLCO amounts must be numeric."
            if not math.isfinite(numeric_value) or numeric_value < 0:
                return "NOLCO amounts cannot be negative."

    return None


# ============================================================
# COMPUTE ONLY (no save)
# ============================================================


@api_bp.route("/compute", methods=["POST"])
@login_required
def compute():
    """
    Compute all three tax schemes without saving anything.
    Safe to call on every keystroke.
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided."}), 400

    parameter_error = validate_tax_parameters(data)
    if parameter_error:
        return jsonify({"error": parameter_error}), 400

    taxpayer_type = data.get("taxpayer_type", "pure")
    if taxpayer_type not in ("pure", "mixed"):
        return jsonify({"error": "Invalid taxpayer type."}), 400

    results, _ = build_results(data)

    return jsonify({
        "results": results,
        "message": "Computation complete.",
    })


# ============================================================
# COMPUTE AND SAVE
# ============================================================


@api_bp.route("/save", methods=["POST"])
@login_required
def save():
    """
    Compute the tax schemes, save the result, and return it
    as JSON. Rejects empty submissions.
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No data provided."}), 400

    parameter_error = validate_tax_parameters(data)
    if parameter_error:
        return jsonify({"error": parameter_error}), 400

    taxpayer_type = data.get("taxpayer_type", "pure")
    if taxpayer_type not in ("pure", "mixed"):
        return jsonify({"error": "Invalid taxpayer type."}), 400

    # Reject empty submissions. A computation with no
    # amounts at all is not meaningful.
    if not has_any_input(data):
        return jsonify({
            "error": "Please enter at least one income or "
                     "deduction amount before saving."
        }), 400

    results, recommendation = build_results(data)

    # Duplicate detection
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=DUPLICATE_WINDOW_MINUTES
    )

    recent_records = (
        Computation.query
        .filter(Computation.user_id == current_user.id)
        .filter(Computation.created_at >= cutoff)
        .all()
    )

    duplicate_of = None
    for record in recent_records:
        if record.inputs == data:
            duplicate_of = record.id
            break

    # Persist
    try:
        computation = Computation(
            user_id=current_user.id,
            taxpayer_type=taxpayer_type,
            inputs=data,
            results=results,
            best_scheme=recommendation["best_scheme"],
            best_tax=recommendation["best_tax"],
        )
        db.session.add(computation)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to save computation."}), 500

    return jsonify({
        "id": computation.id,
        "results": results,
        "duplicate": duplicate_of is not None,
        "duplicate_of": duplicate_of,
        "message": "Computation saved.",
    })


# ============================================================
# LIST SAVED COMPUTATIONS
# ============================================================


@api_bp.route("/history", methods=["GET"])
@login_required
def history():
    """
    Return the current user's saved computations as JSON.
    """
    computations = (
        Computation.query
        .filter_by(user_id=current_user.id)
        .order_by(Computation.created_at.desc())
        .all()
    )

    return jsonify([c.to_dict() for c in computations])


# ============================================================
# ACTIVE TAX TABLE
# ============================================================


@api_bp.route("/tax-table", methods=["GET"])
@login_required
def get_tax_table():
    """Return active graduated tax table brackets."""
    from app.models import TaxBracket

    brackets = (
        TaxBracket.query
        .filter_by(is_active=True)
        .order_by(TaxBracket.threshold.asc())
        .all()
    )

    return jsonify({
        "tax_year": brackets[0].tax_year if brackets else "2023 onwards (TRAIN Law)",
        "brackets": [
            {
                "id": b.id,
                "threshold": b.threshold,
                "upper_amount": b.upper_amount,
                "base_tax": b.base_tax,
                "rate": round(b.rate * 100, 2),
            }
            for b in brackets
        ],
    })