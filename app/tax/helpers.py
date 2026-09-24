# ============================================================
# INPUT EXTRACTION HELPERS
# ============================================================
# The frontend sends raw JSON that may contain strings with
# commas, peso signs, or empty values. These helpers normalize
# the payload into consistent numeric values so that the
# scheme functions do not repeat parsing logic.
#
# Keeping the parsing in one place also makes it easy to
# support new input formats without touching the computation
# code.


def safe_float(value, default=0.0):
    """
    Convert a value to float without raising exceptions.

    Handles strings that contain commas, peso signs, or the
    "PHP" prefix, and returns the default if the value cannot
    be parsed.

    Args:
        value: Any value that may represent a number.
        default (float): Value to return on parse failure.

    Returns:
        float: The parsed number, or the default.
    """
    if value is None or value == "":
        return default

    try:
        cleaned = (
            str(value)
            .replace(",", "")
            .replace("₱", "")
            .replace("PHP", "")
            .strip()
        )
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def peso(value):
    """
    Format a numeric value as a Philippine peso string.

    Args:
        value: Any value that may represent a number.

    Returns:
        str: A string such as "PHP 1,234.50".

    Example:
        peso(1234.5) -> "PHP 1,234.50"
    """
    return f"PHP {safe_float(value):,.2f}"


def get_compensation(data):
    """
    Extract compensation income values for mixed income earners.

    The taxable portion is gross minus non-taxable, floored at
    zero so that over-reported exempt amounts cannot produce a
    negative taxable income.

    Args:
        data (dict): The raw request payload.

    Returns:
        dict: A dictionary with keys "gross", "exempt", and
            "taxable".
    """
    gross = safe_float(data.get("gross_compensation"))
    exempt = safe_float(data.get("non_taxable_compensation"))
    taxable = max(0.0, gross - exempt)

    return {
        "gross": gross,
        "exempt": exempt,
        "taxable": taxable,
    }


def get_sales(data):
    """
    Return total sales or receipts from cash and accrual.

    Both values are added together. The frontend records them
    separately because the BIR form distinguishes cash from
    accrual, but the tax computation only needs the total.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Cash sales plus accrual sales.
    """
    cash = safe_float(data.get("cash_sales"))
    accrual = safe_float(data.get("accrual_sales"))
    return cash + accrual


def get_other_income(data):
    """
    Return the total of all other non-operating income entries.

    The frontend sends this as a list of dictionaries, each
    with a "title" and an "amount". Older payloads may send a
    single numeric value.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Sum of all other income amounts.
    """
    items = data.get("other_income", [])

    # New format: list of {title, amount} dictionaries
    if isinstance(items, list):
        return sum(safe_float(item.get("amount", 0)) for item in items)

    # Legacy format: a single numeric value
    return safe_float(items)


def get_total_cost(data):
    """
    Return total cost of sales or services from cash and
    accrual components.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Cash cost plus accrual cost.
    """
    cash = safe_float(data.get("cash_cost"))
    accrual = safe_float(data.get("accrual_cost"))
    return cash + accrual


def get_ordinary_deductions(data):
    """
    Return the total of ordinary allowable itemized deductions.

    The frontend sends this as a dictionary keyed by deduction
    name, with numeric values. Unknown keys are ignored.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Sum of all ordinary deduction values.
    """
    items = data.get("ordinary_deductions", {})

    if isinstance(items, dict):
        return sum(safe_float(value) for value in items.values())

    return 0.0


def get_special_deductions(data):
    """
    Return the total of special allowable itemized deductions.

    The frontend sends this as a list of {title, amount}
    objects. Empty entries contribute zero.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Sum of all special deduction amounts.
    """
    items = data.get("special_deductions", [])

    if isinstance(items, list):
        return sum(safe_float(item.get("amount", 0)) for item in items)

    return 0.0


def get_nolco_applied(data):
    """
    Return the total Net Operating Loss Carry Over applied for
    the current year.

    The NOLCO schedule follows BIR Form 6.A.1. Column D holds
    the amount applied for the current year. Only this column
    affects the current computation; expired and previously
    applied amounts are recorded for audit purposes.

    Args:
        data (dict): The raw request payload.

    Returns:
        float: Sum of column D across all schedule rows.
    """
    rows = data.get("nolco", [])
    total = 0.0

    if isinstance(rows, list):
        for row in rows:
            total += safe_float(row.get("d", 0))

    return total