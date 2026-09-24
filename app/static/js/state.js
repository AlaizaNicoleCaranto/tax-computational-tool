/* ============================================================
   STATE MODULE
   ============================================================
   Reads the current values from the DOM and produces a
   plain JavaScript object that matches the payload expected
   by the backend /api/calculate endpoint.

   Keeping this logic in one place means that the API module
   and the event handlers do not need to know about element
   ids or class names.
   ============================================================ */

import { parseNumber } from "./utils.js";

/**
 * Read the currently selected taxpayer type.
 *
 * @returns {string} "pure" or "mixed".
 */
export function getTaxpayerType() {
    const checked = document.querySelector(
        'input[name="taxpayerType"]:checked'
    );

    return checked ? checked.value : "pure";
}

/**
 * Collect the other income rows into an array of objects.
 *
 * @returns {Array<{title: string, amount: number}>}
 */
function getOtherIncome() {
    const rows = document.querySelectorAll("#otherIncomeList .dynamic-row");
    const result = [];

    rows.forEach((row) => {
        const title = row.querySelector(".other-income-title").value.trim();
        const amount = parseNumber(
            row.querySelector(".other-income").value
        );

        result.push({ title: title, amount: amount });
    });

    return result;
}

/**
 * Collect the ordinary deduction inputs into a keyed object.
 *
 * @returns {Object<string, number>}
 */
function getOrdinaryDeductions() {
    const inputs = document.querySelectorAll(".ordinary-deduction");
    const result = {};

    inputs.forEach((input) => {
        const name = input.dataset.name;
        if (name) {
            result[name] = parseNumber(input.value);
        }
    });

    return result;
}

/**
 * Collect the special deduction rows into an array of objects.
 *
 * @returns {Array<{title: string, amount: number}>}
 */
function getSpecialDeductions() {
    const rows = document.querySelectorAll(
        "#specialDeductions .dynamic-row"
    );
    const result = [];

    rows.forEach((row) => {
        const title = row.querySelector(".special-title").value.trim();
        const amount = parseNumber(
            row.querySelector(".special-deduction").value
        );

        result.push({ title: title, amount: amount });
    });

    return result;
}

/**
 * Collect the NOLCO schedule rows into an array of objects.
 *
 * @returns {Array<{year: string, a: number, b: number, c: number, d: number}>}
 */
function getNolco() {
    const rows = document.querySelectorAll("#nolcoTableBody tr");
    const result = [];

    rows.forEach((row) => {
        const yearInput = row.querySelector(".year-input");
        const aInput = row.querySelector(".nolco-a");
        const bInput = row.querySelector(".nolco-b");
        const cInput = row.querySelector(".nolco-c");
        const dInput = row.querySelector(".nolco-d");

        // Skip rows that have no data at all.
        const year = yearInput ? yearInput.value.trim() : "";
        const a = aInput ? parseNumber(aInput.value) : 0;
        const b = bInput ? parseNumber(bInput.value) : 0;
        const c = cInput ? parseNumber(cInput.value) : 0;
        const d = dInput ? parseNumber(dInput.value) : 0;

        if (!year && a === 0 && b === 0 && c === 0 && d === 0) {
            return;
        }

        result.push({ year: year, a: a, b: b, c: c, d: d });
    });

    return result;
}

/**
 * Read an input value by id and return it as a number.
 */
function readNumber(id) {
    const element = document.getElementById(id);
    return element ? parseNumber(element.value) : 0;
}

/**
 * Read an input value by id and return it as a string.
 */
function readString(id, fallback) {
    const element = document.getElementById(id);
    if (!element) {
        return fallback;
    }

    const value = element.value.trim();
    return value === "" ? fallback : value;
}

/**
 * Build the full request payload for /api/calculate.
 *
 * The shape matches what the backend expects. Optional
 * fields fall back to the values defined in the Python
 * defaults when left empty.
 *
 * @returns {Object} The request payload.
 */
export function getFormState() {
    return {
        taxpayer_type: getTaxpayerType(),

        // Compensation (mixed income earners only)
        gross_compensation: readNumber("grossComp"),
        non_taxable_compensation: readNumber("nonTaxComp"),

        // Business income
        cash_sales: readNumber("cashSales"),
        accrual_sales: readNumber("accrualSales"),
        other_income: getOtherIncome(),

        // Cost of sales
        cash_cost: readNumber("cashCost"),
        accrual_cost: readNumber("accrualCost"),

        // Itemized deductions
        ordinary_deductions: getOrdinaryDeductions(),
        special_deductions: getSpecialDeductions(),
        nolco: getNolco()
    };
}