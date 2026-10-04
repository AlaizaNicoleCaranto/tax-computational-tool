/* ============================================================
   MAIN MODULE
   ============================================================
   Entry point for the calculator page. Loads the modules,
   caches DOM references, seeds the initial dynamic rows,
   wires events through the events module, and initializes
   the wizard navigation.

   Loaded with type="module" from index.html. All other
   modules are imported below.
   ============================================================ */

import {
    appendNolcoRow,
    appendOtherIncomeRow,
    appendSpecialDeductionRow,
    recomputeNolco
} from "./dynamic-rows.js";

import {
    populateOrdinaryDeductions
} from "./ordinary-deductions.js";

import {
    attachEvents,
    getRowHandlers,
    updateCostDisplay
} from "./events.js";

import {
    attachInputFormatter
} from "./utils.js";

import {
    initializeWizard
} from "./wizard.js";

/* ============================================================
   DOM REFERENCES
   ============================================================ */

const dom = {
    // Taxpayer type
    taxpayerRadios: document.querySelectorAll(
        'input[name="taxpayerType"]'
    ),
    compensationSection: document.getElementById("compensationSection"),

    // Compensation inputs
    grossComp: document.getElementById("grossComp"),
    nonTaxComp: document.getElementById("nonTaxComp"),

    // Business income inputs
    cashSales: document.getElementById("cashSales"),
    accrualSales: document.getElementById("accrualSales"),
    otherIncomeList: document.getElementById("otherIncomeList"),

    // Cost of sales
    cashCost: document.getElementById("cashCost"),
    accrualCost: document.getElementById("accrualCost"),
    totalCostDisplay: document.getElementById("totalCostDisplay"),

    // Itemized deduction containers
    ordinaryDeductions: document.getElementById("ordinaryDeductions"),
    specialDeductions: document.getElementById("specialDeductions"),
    nolcoTableBody: document.getElementById("nolcoTableBody"),
    totalNolcoD: document.getElementById("totalNolcoD"),

    // Result cards
    osdCard: document.getElementById("osdCard"),
    osdResult: document.getElementById("osdResult"),
    itemizedCard: document.getElementById("itemizedCard"),
    itemizedResult: document.getElementById("itemizedResult"),
    eightCard: document.getElementById("eightCard"),
    eightResult: document.getElementById("eightResult"),
    bestScheme: document.getElementById("bestScheme")
};

/* ============================================================
   INITIALIZE
   ============================================================ */

function initialize() {
    const initialState = window.initialTaxFormState || null;

    // 1. Attach the input formatter to every static numeric
    //    input so that thousand separators appear as the
    //    user types.
    [
        dom.grossComp,
        dom.nonTaxComp,
        dom.cashSales,
        dom.accrualSales,
        dom.cashCost,
        dom.accrualCost
    ].forEach(function (input) {
        attachInputFormatter(input);
    });

    // 2. Populate the ordinary deduction grid. The rows
    //    are rendered from a fixed list of names.
    const handlers = getRowHandlers();

    populateOrdinaryDeductions(dom.ordinaryDeductions);

    // 3. Seed the initial rows for the dynamic sections.
    //    Two empty other income rows, one special deduction
    //    row, and four NOLCO rows give the user a starting
    //    point without overwhelming the page.
    appendOtherIncomeRow(dom.otherIncomeList, handlers, "Other Income 1", 0);
    appendOtherIncomeRow(dom.otherIncomeList, handlers, "Other Income 2", 0);

    appendSpecialDeductionRow(dom.specialDeductions, handlers);

    appendNolcoRow(dom.nolcoTableBody, handlers);
    appendNolcoRow(dom.nolcoTableBody, handlers);
    appendNolcoRow(dom.nolcoTableBody, handlers);
    appendNolcoRow(dom.nolcoTableBody, handlers);

    if (initialState) {
        applyInitialState(initialState, handlers);
    }

    // 4. Compute the initial NOLCO schedule so that column
    //    E and the footer total are consistent with the
    //    empty rows that were just added.
    recomputeNolco(dom.nolcoTableBody, dom.totalNolcoD);

    // 5. Wire every event listener through the events
    //    module. This is the last step because it depends
    //    on the DOM being fully populated.
    attachEvents(dom);

    if (initialState && dom.cashSales) {
        dom.cashSales.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // 6. Run an initial cost display update so the cost
    //    summary is correct on first paint.
    updateCostDisplay();

    // 7. Initialize the wizard navigation. This hides every
    //    step except the first one and attaches the Next
    //    and Back button listeners.
    initializeWizard();
}

/* ============================================================
   BOOTSTRAP
   ============================================================
   Wait for the DOM to be parsed before touching elements.
   The script is loaded with type="module" and is deferred,
   so the DOM is usually ready by the time this runs. The
   check is kept for safety.
   ============================================================ */

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
} else {
    initialize();
}

function setInputValue(id, value) {
    const input = document.getElementById(id);
    if (input && value !== undefined && value !== null) {
        input.value = value;
    }
}

function applyInitialState(initialState, handlers) {
    const taxpayerType = initialState.taxpayer_type || "pure";
    dom.taxpayerRadios.forEach(function (radio) {
        radio.checked = radio.value === taxpayerType;
    });

    setInputValue("grossComp", initialState.gross_compensation);
    setInputValue("computationTitle", initialState.computation_title);
    setInputValue("computationNote", initialState.computation_note);
    setInputValue("nonTaxComp", initialState.non_taxable_compensation);
    setInputValue("cashSales", initialState.cash_sales);
    setInputValue("accrualSales", initialState.accrual_sales);
    setInputValue("cashCost", initialState.cash_cost);
    setInputValue("accrualCost", initialState.accrual_cost);

    document.querySelectorAll(".ordinary-deduction").forEach(function (input) {
        const name = input.dataset.name;
        if (name && initialState.ordinary_deductions) {
            input.value = initialState.ordinary_deductions[name] || 0;
        }
    });

    const otherIncome = Array.isArray(initialState.other_income)
        ? initialState.other_income
        : [];
    dom.otherIncomeList.innerHTML = "";
    otherIncome.forEach(function (item) {
        appendOtherIncomeRow(
            dom.otherIncomeList,
            handlers,
            item.title,
            item.amount
        );
    });

    const specialDeductions = Array.isArray(initialState.special_deductions)
        ? initialState.special_deductions
        : [];
    dom.specialDeductions.innerHTML = "";
    specialDeductions.forEach(function (item) {
        appendSpecialDeductionRow(
            dom.specialDeductions,
            handlers,
            item.title,
            item.amount
        );
    });

    const nolco = Array.isArray(initialState.nolco) ? initialState.nolco : [];
    dom.nolcoTableBody.innerHTML = "";
    const nolcoRows = Math.max(4, nolco.length);
    for (let index = 0; index < nolcoRows; index += 1) {
        appendNolcoRow(dom.nolcoTableBody, handlers);
    }

    dom.nolcoTableBody.querySelectorAll("tr").forEach(function (row, index) {
        const savedRow = nolco[index];
        if (!savedRow) {
            return;
        }

        row.querySelector(".year-input").value = savedRow.year || "";
        row.querySelector(".nolco-a").value = savedRow.a || 0;
        row.querySelector(".nolco-b").value = savedRow.b || 0;
        row.querySelector(".nolco-c").value = savedRow.c || 0;
        row.querySelector(".nolco-d").value = savedRow.d || 0;
    });
}