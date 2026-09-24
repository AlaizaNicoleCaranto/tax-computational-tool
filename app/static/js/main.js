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

    // 4. Compute the initial NOLCO schedule so that column
    //    E and the footer total are consistent with the
    //    empty rows that were just added.
    recomputeNolco(dom.nolcoTableBody, dom.totalNolcoD);

    // 5. Wire every event listener through the events
    //    module. This is the last step because it depends
    //    on the DOM being fully populated.
    attachEvents(dom);

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