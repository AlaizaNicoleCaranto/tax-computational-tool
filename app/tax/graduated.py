# ============================================================
# BIR GRADUATED INCOME TAX TABLE
# ============================================================
# Computes the income tax due for an individual taxpayer under
# the graduated rate schedule effective January 1, 2023
# onwards.
#
# Reference: BIR Revenue Regulations implementing the Tax
# Reform for Acceleration and Inclusion (TRAIN) Law.
#
# The table is expressed as a list of brackets. Each bracket
# defines:
#     - upper_limit : the top of the bracket (exclusive)
#     - base_tax    : the fixed tax on the previous brackets
#     - rate        : the marginal rate applied to the excess
#     - threshold   : the amount at which the excess begins
#
# The final bracket uses float("inf") as its upper limit so
# that any income above the last finite threshold is handled.


# Bracket definitions in ascending order.
# Each tuple is (upper_limit, base_tax, rate, threshold).
TAX_BRACKETS = (
    (250000.0, 0.0, 0.00, 0.0),
    (400000.0, 0.0, 0.15, 250000.0),
    (800000.0, 22500.0, 0.20, 400000.0),
    (2000000.0, 102500.0, 0.25, 800000.0),
    (8000000.0, 402500.0, 0.30, 2000000.0),
    (float("inf"), 2202500.0, 0.35, 8000000.0),
)


def compute_graduated_tax(taxable_income):
    """
    Compute the graduated income tax due for the given taxable
    income.

    The function walks the bracket list from lowest to highest
    and returns the tax for the first bracket whose upper limit
    is greater than or equal to the taxable income.

    Args:
        taxable_income (float or str): The taxable income. May
            be a number or a string that can be converted to a
            number. Negative values are treated as zero.

    Returns:
        float: The income tax due, rounded to two decimals.
    """
    # Normalize the input. Any value that cannot be parsed is
    # treated as zero.
    try:
        income = float(
            str(taxable_income).replace(",", "").replace("₱", "").strip()
        )
    except (ValueError, TypeError):
        income = 0.0

    # Negative taxable income is not meaningful; clamp to zero.
    if income <= 0:
        return 0.0

    # Walk the bracket list and return the first match.
    for upper, base_tax, rate, threshold in TAX_BRACKETS:
        if income <= upper:
            # Tax is the base amount plus the rate applied to
            # the portion of income above the threshold.
            excess = income - threshold
            if excess < 0:
                excess = 0
            tax = base_tax + (excess * rate)
            return round(tax, 2)

    # The loop always returns because the final bracket uses
    # infinity as the upper limit. This fallback is unreachable
    # but kept for safety.
    return 0.0