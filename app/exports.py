# ============================================================
# EXPORT ROUTES
# ============================================================
# Generates downloadable files for a saved computation.
#
#     GET /export/pdf/<id>   printable PDF report
#     GET /export/csv/<id>   spreadsheet friendly CSV
#
# Both routes are protected and verify ownership so that a
# user cannot export another user's records.

import csv
import io
from datetime import datetime

from flask import Blueprint, abort, send_file
from flask_login import current_user, login_required

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Computation

# Blueprint with the /export prefix.
exports_bp = Blueprint("exports", __name__, url_prefix="/export")


# ============================================================
# SHARED HELPERS
# ============================================================


def get_owned_computation(computation_id):
    """
    Fetch a computation by id and enforce ownership.

    Returns the computation if it belongs to the current user.
    Aborts with 404 otherwise, so that other users' records
    cannot be probed by guessing ids.
    """
    computation = Computation.query.filter_by(
        id=computation_id,
        user_id=current_user.id,
    ).first()

    if computation is None:
        abort(404)

    return computation


def peso(value):
    """
    Format a numeric value as a Philippine peso string.
    """
    try:
        number = float(value or 0)
    except (ValueError, TypeError):
        number = 0.0

    return f"PHP {number:,.2f}"


def build_scheme_rows(result):
    """
    Convert a scheme result dictionary into an ordered list
    of (label, value) tuples suitable for tables in the PDF
    and CSV exports.

    The shape of the input varies slightly between schemes,
    so each branch decides which rows to include.
    """
    scheme_name = result.get("scheme", "")
    rows = []

    # Include compensation rows for mixed income earners.
    compensation = result.get("compensation")
    if compensation:
        rows.append(
            ("Gross Compensation Income", compensation["gross"])
        )
        rows.append(
            ("Non-Taxable Compensation", compensation["exempt"])
        )
        rows.append(
            ("Taxable Compensation", compensation["taxable"])
        )

    # Scheme 1: Graduated with OSD.
    if "OSD" in scheme_name:
        rows.extend([
            ("Sales / Receipts", result["sales"]),
            (
                f"OSD ({result['osd_percentage']:.2f}%)",
                result["osd_amount"],
            ),
            ("Net Income", result["net_income"]),
            (
                "Other Non-Operating Income",
                result["other_income"],
            ),
            (
                "Total Taxable Income",
                result["total_taxable_income"],
            ),
            ("Income Tax Due", result["income_tax"]),
            (
                f"Percentage Tax ({result['percentage_tax_rate']:.2f}%)",
                result["percentage_tax"],
            ),
            ("TOTAL TAX DUE", result["total_tax"]),
        ])

    # Scheme 2: Graduated with itemized deductions.
    elif "Itemized" in scheme_name:
        rows.extend([
            ("Sales / Receipts", result["sales"]),
            ("Cost of Sales / Services", result["cost"]),
            (
                "Gross Income from Operation",
                result["gross_operation"],
            ),
            (
                "Ordinary Allowable Deductions",
                result["ordinary_deductions"],
            ),
            (
                "Special Allowable Deductions",
                result["special_deductions"],
            ),
            ("NOLCO Applied", result["nolco_applied"]),
            (
                "Total Allowable Deductions",
                result["total_deductions"],
            ),
            ("Net Income", result["net_income"]),
            (
                "Other Non-Operating Income",
                result["other_income"],
            ),
            (
                "Total Taxable Income",
                result["total_taxable_income"],
            ),
            ("Income Tax Due", result["income_tax"]),
            (
                f"Percentage Tax ({result['percentage_tax_rate']:.2f}%)",
                result["percentage_tax"],
            ),
            ("TOTAL TAX DUE", result["total_tax"]),
        ])

    # Scheme 3: Optional 8 percent.
    else:
        if result.get("is_mixed"):
            rows.extend([
                (
                    "Compensation Tax Due",
                    result.get("compensation_tax", 0),
                ),
                ("Gross Business Income", result["gross_income"]),
                (
                    f"Business Tax ({result['flat_rate']:.2f}%)",
                    result["business_tax"],
                ),
            ])
        else:
            rows.extend([
                ("Gross Income", result["gross_income"]),
                (
                    "Standard Deduction",
                    result["standard_deduction"],
                ),
                ("Taxable Income", result["taxable_income"]),
            ])

        rows.append(("TOTAL TAX DUE", result["total_tax"]))

    return rows


# ============================================================
# PDF EXPORT
# ============================================================


@exports_bp.route("/pdf/<int:computation_id>")
@login_required
def export_pdf(computation_id):
    """
    Generate and download a PDF report for one computation.

    The report contains:
        - taxpayer metadata
        - one table per scheme
        - a highlighted recommendation block
        - a disclaimer footer
    """
    computation = get_owned_computation(computation_id)

    # Build the PDF in memory. Using BytesIO avoids writing
    # temporary files to disk.
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
    )

    # Styles used throughout the document.
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#1565c0"),
        alignment=1,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=1,
        textColor=colors.grey,
        spaceAfter=18,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#1565c0"),
        spaceBefore=14,
        spaceAfter=6,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )

    elements = []

    # Title block.
    elements.append(Paragraph("TAX COMPUTATIONAL TOOL", title_style))
    elements.append(
        Paragraph("Tax Scheme Selection Report", subtitle_style)
    )

    # Metadata table.
    taxpayer_type_label = (
        "Purely Single Proprietor / Professional"
        if computation.taxpayer_type == "pure"
        else "Mixed Income Earner"
    )

    meta_rows = [
        ["Taxpayer:", current_user.full_name],
        ["Email:", current_user.email],
        [
            "Date:",
            computation.created_at.strftime("%B %d, %Y %I:%M %p"),
        ],
        ["Classification:", taxpayer_type_label],
    ]

    meta_table = Table(meta_rows, colWidths=[1.5 * inch, 5 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # One table per scheme.
    results = computation.results or {}
    scheme_blocks = [
        ("Scheme 1", results.get("osd", {})),
        ("Scheme 2", results.get("itemized", {})),
        ("Scheme 3", results.get("eight", {})),
    ]

    for label, scheme_result in scheme_blocks:
        scheme_name = scheme_result.get("scheme", label)
        elements.append(
            Paragraph(f"{label}: {scheme_name}", heading_style)
        )

        rows = [["Item", "Amount"]]
        for item_label, value in build_scheme_rows(scheme_result):
            rows.append([item_label, peso(value)])

        table = Table(rows, colWidths=[4.5 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccd3db")),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#f5f8fb")],
            ),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))

    # Recommendation block.
    rec_rows = [
        ["RECOMMENDATION", ""],
        ["Best Scheme:", results.get("best_scheme", "")],
        ["Total Tax Due:", peso(results.get("best_tax", 0))],
    ]
    rec_table = Table(rec_rows, colWidths=[2 * inch, 4.5 * inch])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e7d32")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("SPAN", (0, 0), (-1, 0)),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2e7d32")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#e8f5e9")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(rec_table)
    elements.append(Spacer(1, 18))

    # Disclaimer footer.
    elements.append(Paragraph(
        "Generated by Tax Computational Tool | "
        "Project by: Ella Mae A. Deriquito & Karylle M. Diaz<br/>"
        "This computation is for reference only. Please consult "
        "with a licensed accountant or the BIR for official "
        "tax advice.",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    filename = (
        f"tax_computation_{computation.id}_"
        f"{datetime.now().strftime('%Y%m%d')}.pdf"
    )

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


# ============================================================
# CSV EXPORT
# ============================================================


@exports_bp.route("/csv/<int:computation_id>")
@login_required
def export_csv(computation_id):
    """
    Generate and download a CSV report for one computation.

    The CSV structure mirrors the PDF:
        - header metadata
        - one section per scheme
        - a recommendation block
    """
    computation = get_owned_computation(computation_id)

    # Build the CSV in memory.
    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata.
    writer.writerow(["TAX COMPUTATIONAL TOOL - COMPUTATION REPORT"])
    writer.writerow([])
    writer.writerow(["Taxpayer", current_user.full_name])
    writer.writerow(["Email", current_user.email])
    writer.writerow([
        "Date",
        computation.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    ])
    writer.writerow([
        "Classification",
        "Purely Single Proprietor"
        if computation.taxpayer_type == "pure"
        else "Mixed Income Earner",
    ])
    writer.writerow([])

    results = computation.results or {}

    scheme_blocks = [
        ("Scheme 1", results.get("osd", {})),
        ("Scheme 2", results.get("itemized", {})),
        ("Scheme 3", results.get("eight", {})),
    ]

    for label, scheme_result in scheme_blocks:
        scheme_name = scheme_result.get("scheme", label)
        writer.writerow([f"{label}: {scheme_name}"])
        writer.writerow(["Item", "Amount (PHP)"])

        for item_label, value in build_scheme_rows(scheme_result):
            try:
                numeric = float(value or 0)
            except (ValueError, TypeError):
                numeric = 0.0
            writer.writerow([item_label, f"{numeric:.2f}"])

        writer.writerow([])

    # Recommendation block.
    writer.writerow(["RECOMMENDATION"])
    writer.writerow(["Best Scheme", results.get("best_scheme", "")])
    writer.writerow([
        "Total Tax",
        f"{float(results.get('best_tax', 0) or 0):.2f}",
    ])

    output.seek(0)

    filename = (
        f"tax_computation_{computation.id}_"
        f"{datetime.now().strftime('%Y%m%d')}.csv"
    )

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        as_attachment=True,
        download_name=filename,
        mimetype="text/csv",
    )