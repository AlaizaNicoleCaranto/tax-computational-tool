/* ============================================================
   RENDER MODULE
   ============================================================
   Converts the JSON results from /api/calculate into HTML
   for the three scheme cards and the recommendation block.

   The module only builds HTML strings. It does not read
   from or write to the DOM except through the small set of
   render functions exported at the bottom.
   ============================================================ */

import { formatNumber, formatPeso } from "./utils.js";

/* ============================================================
   PRIMITIVES
   ============================================================ */

/**
 * Escape a value for safe insertion into HTML.
 *
 * All dynamic values pass through this function before
 * being placed into a template literal so that untrusted
 * input cannot inject markup.
 *
 * @param {*} value
 * @returns {string}
 */
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

/**
 * Build one compute-row block.
 *
 * @param {string} label
 * @param {string} amount - Pre-formatted amount string.
 * @param {string} [className] - Extra class names.
 * @returns {string}
 */
function row(label, amount, className) {
    const classes = ["compute-row"];
    if (className) {
        classes.push(className);
    }

    return (
        '<div class="' + classes.join(" ") + '">' +
        "<span>" + escapeHtml(label) + "</span>" +
        '<span class="amount">' + escapeHtml(amount) + "</span>" +
        "</div>"
    );
}

/**
 * Build one compute-row block with a peso formatted amount.
 */
function pesoRow(label, value, className) {
    return row(label, formatPeso(value), className);
}

/**
 * Build an editable numeric setting row for a tax scheme.
 */
function settingRow(label, setting, value, suffix) {
    const numericValue = Number(value);
    const inputValue = Number.isFinite(numericValue)
        ? numericValue
        : 0;

    return (
        '<div class="compute-row result-setting">' +
        "<span>" + escapeHtml(label) + "</span>" +
        '<span class="setting-control">' +
        '<input type="number" class="setting-input" ' +
        'data-setting="' + escapeHtml(setting) + '" ' +
        'value="' + escapeHtml(inputValue) + '" ' +
        'min="0" step="0.01" inputmode="decimal">' +
        '<span class="setting-suffix">' +
        escapeHtml(suffix) +
        "</span></span></div>"
    );
}

/* ============================================================
   SCHEME 1: OSD
   ============================================================ */

function renderOsd(result) {
    const parts = [];

    if (result.compensation) {
        parts.push(pesoRow(
            "Gross Compensation Income",
            result.compensation.gross
        ));
        parts.push(pesoRow(
            "Non-Taxable Compensation",
            result.compensation.exempt
        ));
        parts.push(pesoRow(
            "Taxable Compensation",
            result.compensation.taxable
        ));
    }

    parts.push(pesoRow("Sales / Receipts", result.sales));
    parts.push(settingRow(
        "OSD Percentage",
        "osd_percentage",
        result.osd_percentage,
        "%"
    ));
    parts.push(pesoRow("OSD Amount", result.osd_amount));
    parts.push(pesoRow("Net Income", result.net_income, "subtotal"));
    parts.push(pesoRow(
        "Other Non-Operating Income",
        result.other_income
    ));
    parts.push(pesoRow("Taxable Income", result.business_taxable));

    if (result.is_mixed) {
        parts.push(pesoRow(
            "Total Taxable Income",
            result.total_taxable_income,
            "subtotal"
        ));
    }

    parts.push(pesoRow("Income Tax Due", result.income_tax));
    parts.push(settingRow(
        "Percentage Tax Rate",
        "percentage_tax_rate",
        result.percentage_tax_rate,
        "%"
    ));
    parts.push(pesoRow("Percentage Tax Due", result.percentage_tax));
    parts.push(row(
        "TOTAL TAX DUES",
        formatPeso(result.total_tax),
        "total"
    ));

    return parts.join("");
}

/* ============================================================
   SCHEME 2: ITEMIZED
   ============================================================ */

function renderItemized(result) {
    const parts = [];

    if (result.compensation) {
        parts.push(pesoRow(
            "Gross Compensation Income",
            result.compensation.gross
        ));
        parts.push(pesoRow(
            "Non-Taxable Compensation",
            result.compensation.exempt
        ));
        parts.push(pesoRow(
            "Taxable Compensation",
            result.compensation.taxable
        ));
    }

    parts.push(pesoRow("Sales / Receipts", result.sales));
    parts.push(pesoRow("Cost of Sales / Services", result.cost));
    parts.push(pesoRow(
        "Gross Income from Operation",
        result.gross_operation,
        "subtotal"
    ));
    parts.push(pesoRow(
        "Ordinary Allowable Deductions",
        result.ordinary_deductions
    ));
    parts.push(pesoRow(
        "Special Allowable Deductions",
        result.special_deductions
    ));
    parts.push(pesoRow("NOLCO Applied", result.nolco_applied));
    parts.push(pesoRow(
        "Total Allowable Itemized Deduction",
        result.total_deductions,
        "subtotal"
    ));
    parts.push(pesoRow("Net Income", result.net_income, "subtotal"));
    parts.push(pesoRow(
        "Other Non-Operating Income",
        result.other_income
    ));
    parts.push(pesoRow("Taxable Income", result.business_taxable));

    if (result.is_mixed) {
        parts.push(pesoRow(
            "Total Taxable Income",
            result.total_taxable_income,
            "subtotal"
        ));
    }

    parts.push(pesoRow("Income Tax Due", result.income_tax));
    parts.push(settingRow(
        "Percentage Tax Rate",
        "percentage_tax_rate",
        result.percentage_tax_rate,
        "%"
    ));
    parts.push(pesoRow("Percentage Tax Due", result.percentage_tax));
    parts.push(row(
        "TOTAL TAX DUES",
        formatPeso(result.total_tax),
        "total"
    ));

    return parts.join("");
}

/* ============================================================
   SCHEME 3: OPTIONAL 8 PERCENT
   ============================================================ */

function renderEight(result) {
    const parts = [];

    if (result.is_mixed) {
        parts.push(pesoRow(
            "Gross Compensation Income",
            result.compensation.gross
        ));
        parts.push(pesoRow(
            "Non-Taxable Compensation",
            result.compensation.exempt
        ));
        parts.push(pesoRow(
            "Taxable Compensation",
            result.compensation.taxable
        ));
        parts.push(pesoRow(
            "Compensation Tax Due",
            result.compensation_tax
        ));
        parts.push(pesoRow("Sales / Receipts", result.sales));
        parts.push(pesoRow(
            "Other Non-Operating Income",
            result.other_income
        ));
        parts.push(pesoRow(
            "Gross Income / Taxable Income",
            result.gross_income
        ));
        parts.push(row(
            "Tax Rate (" + formatNumber(result.flat_rate) + "%)",
            formatPeso(result.business_tax)
        ));
    } else {
        parts.push(pesoRow("Sales / Receipts", result.sales));
        parts.push(pesoRow(
            "Other Non-Operating Income",
            result.other_income
        ));
        parts.push(pesoRow(
            "Gross Income",
            result.gross_income,
            "subtotal"
        ));
        parts.push(settingRow(
            "Standard Deduction",
            "standard_deduction",
            result.standard_deduction,
            ""
        ));
        parts.push(pesoRow(
            "Taxable Income",
            result.taxable_income
        ));
        parts.push(settingRow(
            "Tax Rate",
            "flat_rate",
            result.flat_rate,
            "%"
        ));
        parts.push(pesoRow("Tax Due", result.income_tax));
    }

    if (result.vat_warning) {
        parts.push(
            '<div class="vat-warning">' +
                "Gross income exceeds PHP 3,000,000. This " +
                "optional rate is not available to VAT-registered " +
            "taxpayers or those exceeding the VAT " +
            "threshold. Please verify eligibility with " +
            "the BIR." +
            "</div>"
        );
    }

    parts.push(row(
        "TOTAL TAX DUES",
        formatPeso(result.total_tax),
        "total"
    ));

    return parts.join("");
}

/* ============================================================
   RECOMMENDATION
   ============================================================ */

function renderRecommendation(bestScheme, bestTax) {
    return (
        "<strong>Comparison Result</strong><br>" +
        "Based on the figures entered, the lowest calculated " +
        "total among the three schemes is " +
        "<strong>" + escapeHtml(bestScheme) + "</strong> " +
        "with a calculated amount of " +
        "<strong>" + formatPeso(bestTax) + "</strong>." +
        "<br><br>" +
        "This comparison is only a mathematical comparison of " +
        "the figures entered. Actual eligibility, tax-option " +
        "requirements, documentation, and applicable BIR " +
        "rules must still be checked."
    );
}

/* ============================================================
   PUBLIC RENDER FUNCTION
   ============================================================ */

/**
 * Render all three scheme cards and the recommendation.
 *
 * @param {Object} results - The results object from the API.
 * @param {Object} dom - Cached DOM references.
 */
export function renderResults(results, dom) {
    if (!results) {
        return;
    }

    if (dom.osdResult) {
        dom.osdResult.innerHTML = renderOsd(results.osd);
    }

    if (dom.itemizedResult) {
        dom.itemizedResult.innerHTML = renderItemized(results.itemized);
    }

    if (dom.eightResult) {
        dom.eightResult.innerHTML = renderEight(results.eight);
    }

    if (dom.bestScheme) {
        dom.bestScheme.innerHTML = renderRecommendation(
            results.best_scheme,
            results.best_tax
        );
    }

    // Highlight the best scheme card.
    highlightBestCard(results.best_scheme, dom);
}

/**
 * Add the is-best class to whichever card matches the
 * recommended scheme, and remove it from the others.
 */
function highlightBestCard(bestScheme, dom) {
    const cards = [
        { element: dom.osdCard, name: "OSD" },
        { element: dom.itemizedCard, name: "Itemized" },
        { element: dom.eightCard, name: "Optional" }
    ];

    cards.forEach(function (card) {
        if (!card.element) {
            return;
        }

        const isBest = bestScheme &&
            bestScheme.toLowerCase().includes(card.name.toLowerCase());

        card.element.classList.toggle("is-best", Boolean(isBest));
    });
}