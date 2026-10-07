# ============================================================
# TAX COMPUTATION PACKAGE
# ============================================================
# Groups the tax related modules into a single importable
# package:
#
#     graduated : BIR graduated income tax table
#     helpers   : input normalization utilities
#     schemes   : the three tax scheme computations
#
# Re-exporting the public functions here keeps import paths
# short and consistent across the application.

from app.tax.graduated import (
    compute_graduated_breakdown,
    compute_graduated_tax,
)
from app.tax.schemes import (
    compute_eight_percent,
    compute_itemized,
    compute_osd,
    recommend_scheme,
)

# Public API of the package.
__all__ = [
    "compute_graduated_breakdown",
    "compute_graduated_tax",
    "compute_osd",
    "compute_itemized",
    "compute_eight_percent",
    "recommend_scheme",
]