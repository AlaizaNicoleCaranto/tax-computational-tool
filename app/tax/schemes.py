# ============================================================
# TAX SCHEME COMPUTATIONS
# ============================================================
# Three schemes are computed for every taxpayer so that the
# system can recommend the one with the lowest total tax.
#
# Scheme 1: Graduated income tax with Optional Standard
#           Deduction (OSD) and percentage tax.
# Scheme 2: Graduated income tax with Itemized Deductions
#           and percentage tax.
# Scheme 3: Optional 8% income tax rate in lieu of the
#           graduated income tax and percentage tax.
#
# Each scheme returns a dictionary with consistent keys so
# that the recommendation logic and the frontend can treat
# them uniformly.

from app.tax.graduated import compute_graduated_breakdown
from app.tax.helpers import (
    get_compensation,
    get_nolco_applied,
    get_ordinary_deductions,
    get_other_income,
    get_sales,
    get_special_deductions,
    get_total_cost,
    safe_float,
)

# Default values used when the frontend does not override.
DEFAULT_OSD_PERCENTAGE = 40.0
DEFAULT_PERCENTAGE_TAX_RATE = 3.0
DEFAULT_STANDARD_DEDUCTION = 250000.0
DEFAULT_FLAT_RATE = 8.0

# VAT registration threshold for individual taxpayers.
VAT_THRESHOLD = 3000000.0


def get_tax_table_values(data, prefix=None, taxable_income=None):
    """
    Return automatic tax-table values computed directly from the graduated tax table.
    Manual overrides are not applied; computations are strictly based on the tax table.
    """
    income = data if taxable_income is None else taxable_income
    automatic = compute_graduated_breakdown(income)

    return {
        "bracket_index": automatic.get("bracket_index", 1),
        "threshold": automatic.get("threshold", 0.0),
        "upper_amount": automatic.get("upper_amount"),
        "basic_tax": automatic.get("base_tax", 0.0),
        "excess_amount": automatic.get("excess_amount", 0.0),
        "excess_rate": automatic.get("excess_rate", 0.0),
        "income_tax": automatic.get("income_tax", 0.0),
        "basic_tax_custom": False,
        "excess_amount_custom": False,
        "excess_rate_custom": False,
    }


# ============================================================
# SCHEME 1: GRADUATED TAX WITH OSD AND PERCENTAGE TAX
# ============================================================


def compute_osd(data):
    """
    Compute Scheme 1: graduated income tax with the Optional
    Standard Deduction and percentage tax.

    Steps:
        1. Sales minus OSD equals net income from operation.
        2. Add other non-operating income to get taxable income.
        3. Add taxable compensation for mixed income earners.
        4. Apply the graduated tax table to get income tax due.
        5. Apply percentage tax on gross income.

    Args:
        data (dict): The raw request payload.

    Returns:
        dict: The computation result for this scheme.
    """
    # Determine whether the taxpayer is a mixed income earner.
    is_mixed = data.get("taxpayer_type") == "mixed"

    # Compensation values are only relevant for mixed earners.
    compensation = get_compensation(data) if is_mixed else None

    # Business income components.
    sales = get_sales(data)
    other_income = get_other_income(data)

    # OSD percentage. Defaults to 40 percent but the user may
    # override this in the interface.
    osd_percentage = safe_float(
        data.get("osd_percentage", DEFAULT_OSD_PERCENTAGE)
    )
    if osd_percentage < 0:
        osd_percentage = DEFAULT_OSD_PERCENTAGE

    # Apply the OSD to sales to get the deductible amount.
    osd_amount = sales * (osd_percentage / 100)

    # Net income is sales minus OSD, floored at zero.
    net_income = max(0.0, sales - osd_amount)

    # Business taxable income includes other non-operating
    # income. Other income is not eligible for the OSD, so it
    # is added after the deduction is applied.
    business_taxable = net_income + other_income

    # For mixed income earners, add taxable compensation.
    if is_mixed:
        total_taxable = business_taxable + compensation["taxable"]
    else:
        total_taxable = business_taxable

    tax_table = get_tax_table_values(data, "osd", total_taxable)
    income_tax = tax_table["income_tax"]

    # Percentage tax rate. Defaults to 3 percent. The rate may
    # be reduced under special laws, so the frontend may
    # override it.
    percentage_rate = safe_float(
        data.get("percentage_tax_rate", DEFAULT_PERCENTAGE_TAX_RATE)
    )
    if percentage_rate < 0:
        percentage_rate = DEFAULT_PERCENTAGE_TAX_RATE

    # Percentage tax base is gross sales plus other income.
    gross_for_percentage = sales + other_income
    percentage_tax = gross_for_percentage * (percentage_rate / 100)

    # Total tax due for this scheme.
    total_tax = income_tax + percentage_tax

    return {
        "scheme": (
            "Graduated Income Tax with OSD and Percentage Tax"
        ),
        "is_mixed": is_mixed,
        "compensation": compensation,
        "sales": sales,
        "osd_percentage": osd_percentage,
        "osd_amount": osd_amount,
        "net_income": net_income,
        "other_income": other_income,
        "business_taxable": business_taxable,
        "total_taxable_income": total_taxable,
        "basic_tax": tax_table["basic_tax"],
        "excess_amount": tax_table["excess_amount"],
        "excess_rate": tax_table["excess_rate"],
        "basic_tax_custom": tax_table["basic_tax_custom"],
        "excess_amount_custom": tax_table["excess_amount_custom"],
        "excess_rate_custom": tax_table["excess_rate_custom"],
        "bracket_index": tax_table["bracket_index"],
        "threshold": tax_table["threshold"],
        "upper_amount": tax_table["upper_amount"],
        "income_tax": income_tax,
        "percentage_tax_rate": percentage_rate,
        "percentage_tax": percentage_tax,
        "total_tax": total_tax,
    }


# ============================================================
# SCHEME 2: GRADUATED TAX WITH ITEMIZED DEDUCTIONS
# ============================================================


def compute_itemized(data):
    """
    Compute Scheme 2: graduated income tax with Itemized
    Deductions and percentage tax.

    Steps:
        1. Sales minus cost of sales equals gross income.
        2. Subtract ordinary, special, and NOLCO deductions.
        3. Add other non-operating income to get taxable income.
        4. Add taxable compensation for mixed income earners.
        5. Apply the graduated tax table to get income tax due.
        6. Apply percentage tax on gross income.

    Args:
        data (dict): The raw request payload.

    Returns:
        dict: The computation result for this scheme.
    """
    # Determine whether the taxpayer is a mixed income earner.
    is_mixed = data.get("taxpayer_type") == "mixed"

    # Compensation values are only relevant for mixed earners.
    compensation = get_compensation(data) if is_mixed else None

    # Business income components.
    sales = get_sales(data)
    other_income = get_other_income(data)

    # Cost of sales or services.
    cost = get_total_cost(data)

    # Gross income from operation is sales minus cost. Floored
    # at zero so that negative gross income does not produce a
    # refund in the calculation.
    gross_operation = max(0.0, sales - cost)

    # Itemized deduction components.
    ordinary = get_ordinary_deductions(data)
    special = get_special_deductions(data)
    nolco = get_nolco_applied(data)

    # Total allowable itemized deductions.
    total_deductions = ordinary + special + nolco

    # Net income after all deductions, floored at zero.
    net_income = max(0.0, gross_operation - total_deductions)

    # Business taxable income includes other non-operating
    # income. Other income is not reduced by itemized
    # deductions, so it is added after the deductions are
    # applied.
    business_taxable = net_income + other_income

    # For mixed income earners, add taxable compensation.
    if is_mixed:
        total_taxable = business_taxable + compensation["taxable"]
    else:
        total_taxable = business_taxable

    tax_table = get_tax_table_values(data, "itemized", total_taxable)
    income_tax = tax_table["income_tax"]

    # Percentage tax rate. Defaults to 3 percent.
    percentage_rate = safe_float(
        data.get("percentage_tax_rate", DEFAULT_PERCENTAGE_TAX_RATE)
    )
    if percentage_rate < 0:
        percentage_rate = DEFAULT_PERCENTAGE_TAX_RATE

    # Percentage tax base is gross sales plus other income.
    gross_for_percentage = sales + other_income
    percentage_tax = gross_for_percentage * (percentage_rate / 100)

    # Total tax due for this scheme.
    total_tax = income_tax + percentage_tax

    return {
        "scheme": (
            "Graduated Income Tax with Itemized Deduction "
            "and Percentage Tax"
        ),
        "is_mixed": is_mixed,
        "compensation": compensation,
        "sales": sales,
        "cost": cost,
        "gross_operation": gross_operation,
        "ordinary_deductions": ordinary,
        "special_deductions": special,
        "nolco_applied": nolco,
        "total_deductions": total_deductions,
        "net_income": net_income,
        "other_income": other_income,
        "business_taxable": business_taxable,
        "total_taxable_income": total_taxable,
        "basic_tax": tax_table["basic_tax"],
        "excess_amount": tax_table["excess_amount"],
        "excess_rate": tax_table["excess_rate"],
        "basic_tax_custom": tax_table["basic_tax_custom"],
        "excess_amount_custom": tax_table["excess_amount_custom"],
        "excess_rate_custom": tax_table["excess_rate_custom"],
        "bracket_index": tax_table["bracket_index"],
        "threshold": tax_table["threshold"],
        "upper_amount": tax_table["upper_amount"],
        "income_tax": income_tax,
        "percentage_tax_rate": percentage_rate,
        "percentage_tax": percentage_tax,
        "total_tax": total_tax,
    }


# ============================================================
# SCHEME 3: OPTIONAL 8% INCOME TAX RATE
# ============================================================


def compute_eight_percent(data):
    """
    Compute Scheme 3: the optional 8% income tax rate in lieu
    of the graduated income tax and percentage tax.

    For purely business or professional taxpayers:
        Gross sales or receipts plus other income, minus the
        standard deduction of 250,000, times 8 percent.

    For mixed income earners:
        Compensation is taxed under the graduated table, and
        business income is taxed at 8 percent of gross.

    A warning flag is set when gross income exceeds 3,000,000
    because the 8 percent option is not available to
    VAT-registered taxpayers or those exceeding the VAT
    threshold. The computation still runs so that the user
    can see the comparison, but the interface must display
    the warning.

    Args:
        data (dict): The raw request payload.

    Returns:
        dict: The computation result for this scheme.
    """
    # Determine whether the taxpayer is a mixed income earner.
    is_mixed = data.get("taxpayer_type") == "mixed"

    # Compensation values are only relevant for mixed earners.
    compensation = get_compensation(data) if is_mixed else None

    # Business income components.
    sales = get_sales(data)
    other_income = get_other_income(data)

    # Gross business income. The 8 percent rate applies to
    # gross sales and receipts plus other non-operating income.
    gross_income = sales + other_income

    # Standard deduction. Defaults to 250,000 for purely
    # business or professional taxpayers. Mixed income earners
    # do not get the standard deduction because it is already
    # applied to their compensation income.
    standard_deduction = safe_float(
        data.get("standard_deduction", DEFAULT_STANDARD_DEDUCTION)
    )
    if standard_deduction < 0:
        standard_deduction = DEFAULT_STANDARD_DEDUCTION

    # Flat rate. Defaults to 8 percent.
    flat_rate = safe_float(data.get("flat_rate", DEFAULT_FLAT_RATE))
    if flat_rate < 0:
        flat_rate = DEFAULT_FLAT_RATE

    scheme_name = f"Optional Income Tax Rate ({flat_rate:g}%)"

    # VAT threshold check. Used only for the warning flag.
    exceeds_vat_threshold = gross_income > VAT_THRESHOLD

    # Purely business or professional taxpayer.
    if not is_mixed:
        taxable = max(0.0, gross_income - standard_deduction)
        tax = taxable * (flat_rate / 100)

        return {
            "scheme": scheme_name,
            "is_mixed": False,
            "compensation": None,
            "sales": sales,
            "other_income": other_income,
            "gross_income": gross_income,
            "standard_deduction": standard_deduction,
            "taxable_income": taxable,
            "flat_rate": flat_rate,
            "income_tax": tax,
            "total_tax": tax,
            "vat_warning": exceeds_vat_threshold,
        }

    # Mixed income earner: compensation is taxed under the
    # graduated table, business income at 8 percent.
    compensation_table = get_tax_table_values(
        data,
        "compensation",
        compensation["taxable"],
    )
    compensation_tax = compensation_table["income_tax"]
    business_tax = gross_income * (flat_rate / 100)
    total_tax = compensation_tax + business_tax

    return {
        "scheme": scheme_name,
        "is_mixed": True,
        "compensation": compensation,
        "compensation_tax": compensation_tax,
        "basic_tax": compensation_table["basic_tax"],
        "excess_amount": compensation_table["excess_amount"],
        "excess_rate": compensation_table["excess_rate"],
        "basic_tax_custom": compensation_table["basic_tax_custom"],
        "excess_amount_custom": compensation_table["excess_amount_custom"],
        "excess_rate_custom": compensation_table["excess_rate_custom"],
        "bracket_index": compensation_table["bracket_index"],
        "threshold": compensation_table["threshold"],
        "upper_amount": compensation_table["upper_amount"],
        "sales": sales,
        "other_income": other_income,
        "gross_income": gross_income,
        "flat_rate": flat_rate,
        "business_tax": business_tax,
        "income_tax": compensation_tax,
        "total_tax": total_tax,
        "vat_warning": exceeds_vat_threshold,
    }


# ============================================================
# RECOMMENDATION
# ============================================================


def recommend_scheme(osd_result, itemized_result, eight_result):
    """
    Compare the three computed schemes and return the one with
    the lowest total tax.

    The 8 percent scheme is still considered even when the VAT
    threshold is exceeded, but the frontend should display a
    warning so that the user can verify eligibility.

    Args:
        osd_result (dict): Result from compute_osd.
        itemized_result (dict): Result from compute_itemized.
        eight_result (dict): Result from compute_eight_percent.

    Returns:
        dict: A dictionary with "best_scheme" and "best_tax".
    """
    candidates = [
        (osd_result["scheme"], osd_result["total_tax"]),
        (itemized_result["scheme"], itemized_result["total_tax"]),
    ]

    if not eight_result.get("vat_warning"):
        candidates.append((eight_result["scheme"], eight_result["total_tax"]))

    # Pick the tuple with the smallest total tax.
    best_name, best_tax = min(candidates, key=lambda pair: pair[1])

    return {
        "best_scheme": best_name,
        "best_tax": best_tax,
    }