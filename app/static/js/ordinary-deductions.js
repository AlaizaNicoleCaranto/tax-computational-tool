/* ============================================================
   ORDINARY DEDUCTIONS MODULE
   ============================================================
   Populates the ordinary allowable itemized deductions grid
   with one row per deduction name.

   The list of names lives here so that it stays in one
   place. The HTML for this grid is intentionally empty and
   is filled at page load.

   Input events are handled through the delegated listener
   in events.js, so no per-input listeners are attached here.
   ============================================================ */

import { attachInputFormatter } from "./utils.js";

export const ORDINARY_DEDUCTION_NAMES = [
    "Amortizations",
    "Bad Debts",
    "Charitable and Other Contributions",
    "Depletion",
    "Depreciation",
    "Entertainment, Amusement and Recreation",
    "Fringe Benefits",
    "Interest",
    "Losses",
    "Pension Trusts",
    "Rental",
    "Research and Development",
    "Salaries, Wages and Allowances",
    "SSS, GSIS, PhilHealth, HDMF and Other Contributions",
    "Taxes and Licenses",
    "Transportation and Travel",
    "Janitorial and Messengerial Services",
    "Professional Fees",
    "Security Services",
    "Other Expenses"
];

export function populateOrdinaryDeductions(container) {
    if (!container) {
        return;
    }

    // Clear any existing rows so the function is idempotent.
    container.innerHTML = "";

    ORDINARY_DEDUCTION_NAMES.forEach(function (name) {
        const row = document.createElement("div");
        row.className = "deduction-row";

        const label = document.createElement("label");
        label.textContent = name;

        const input = document.createElement("input");
        input.type = "text";
        input.className = "ordinary-deduction";
        input.value = "0";
        input.inputMode = "decimal";
        input.dataset.name = name;

        attachInputFormatter(input);

        row.appendChild(label);
        row.appendChild(input);
        container.appendChild(row);
    });
}