/* ============================================================
   EVENTS MODULE
   ============================================================ */

import {
    appendNolcoRow,
    appendOtherIncomeRow,
    appendSpecialDeductionRow,
    recomputeNolco
} from "./dynamic-rows.js";

import { getFormState, getTaxpayerType } from "./state.js";
import { computeTax, fetchTaxTable, saveTax } from "./api.js";
import { renderResults } from "./render.js";
import { debounce } from "./utils.js";
import { showToast } from "./toast.js";

/* ============================================================
   CONSTANTS
   ============================================================ */

const AUTO_COMPUTE_DELAY = 600;
const AUTO_RESET_DELAY = 1500;

/* ============================================================
   MODULE STATE
   ============================================================ */

let dom = null;
let autoCompute = null;

/* ============================================================
   TAXPAYER TYPE TOGGLE
   ============================================================ */

function syncCompensationVisibility() {
    if (!dom.compensationSection) {
        return;
    }

    const isMixed = getTaxpayerType() === "mixed";
    dom.compensationSection.classList.toggle("hidden", !isMixed);
}

/* ============================================================
   DYNAMIC ROW HANDLERS
   ============================================================ */

function buildRowHandlers() {
    return {
        onRemove: function () {
            if (typeof autoCompute === "function") {
                autoCompute();
            }
        },
        onChange: function () {
            if (typeof autoCompute === "function") {
                autoCompute();
            }
        },
        onNolcoChange: function () {
            recomputeNolco(dom.nolcoTableBody, dom.totalNolcoD);
            if (typeof autoCompute === "function") {
                autoCompute();
            }
        }
    };
}

/* ============================================================
   COST DISPLAY
   ============================================================ */

function updateCostDisplay() {
    if (!dom.totalCostDisplay) {
        return;
    }

    const cash = parseFloatSafe(dom.cashCost ? dom.cashCost.value : 0);
    const accrual = parseFloatSafe(
        dom.accrualCost ? dom.accrualCost.value : 0
    );
    const total = cash + accrual;

    dom.totalCostDisplay.textContent =
        "PHP " +
        total.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
}

function formatTaxTableAmount(value) {
    return Number(value || 0).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function renderTaxTableModal(brackets) {
    const tableBody = document.getElementById("taxReferenceBody");
    if (!tableBody || !Array.isArray(brackets)) {
        return;
    }

    tableBody.innerHTML = "";

    brackets.forEach(function (bracket) {
        const row = document.createElement("tr");

        const thresholdCell = document.createElement("td");
        thresholdCell.style.textAlign = "right";
        thresholdCell.textContent = Number(bracket.threshold) === 0
            ? "-"
            : "₱" + formatTaxTableAmount(bracket.threshold);

        const upperCell = document.createElement("td");
        upperCell.style.textAlign = "right";
        upperCell.textContent = bracket.upper_amount === null ||
            bracket.upper_amount === undefined
            ? "and above"
            : "₱" + formatTaxTableAmount(bracket.upper_amount);

        const rateCell = document.createElement("td");
        rateCell.style.textAlign = "left";
        const rate = Number(bracket.rate || 0);
        const baseTax = Number(bracket.base_tax || 0);
        const threshold = formatTaxTableAmount(bracket.threshold);

        if (rate === 0) {
            rateCell.textContent = "0%";
        } else if (baseTax === 0) {
            rateCell.textContent = rate + "% of excess over ₱" + threshold;
        } else {
            rateCell.textContent = "₱" + formatTaxTableAmount(baseTax) +
                " + " + rate + "% of excess over ₱" + threshold;
        }

        row.appendChild(thresholdCell);
        row.appendChild(upperCell);
        row.appendChild(rateCell);
        tableBody.appendChild(row);
    });
}

function parseFloatSafe(value) {
    if (value === null || value === undefined) {
        return 0;
    }

    const cleaned = String(value)
        .replace(/,/g, "")
        .replace(/₱/g, "")
        .replace(/PHP/gi, "")
        .trim();

    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
}

/* ============================================================
   COMPUTATION
   ============================================================ */

async function computeOnly() {
    if (!dom.bestScheme) {
        return;
    }

    try {
        const payload = getFormState();
        const response = await computeTax(payload);
        renderResults(response.results, dom);
        updateCostDisplay();
    } catch (error) {
        dom.bestScheme.textContent =
            "Could not compute the tax. " +
            (error && error.message ? error.message : "");
    }
}

/**
 * Check whether the payload contains at least one non-zero
 * value. Returns true if there is data to save.
 */
function hasAnyInput(payload) {
    if (payload.gross_compensation > 0) return true;
    if (payload.non_taxable_compensation > 0) return true;
    if (payload.cash_sales > 0) return true;
    if (payload.accrual_sales > 0) return true;
    if (payload.cash_cost > 0) return true;
    if (payload.accrual_cost > 0) return true;

    if (Array.isArray(payload.other_income)) {
        const total = payload.other_income.reduce(function (sum, item) {
            return sum + (Number(item.amount) || 0);
        }, 0);
        if (total > 0) return true;
    }

    if (payload.ordinary_deductions &&
        typeof payload.ordinary_deductions === "object") {
        const values = Object.values(payload.ordinary_deductions);
        const total = values.reduce(function (sum, v) {
            return sum + (Number(v) || 0);
        }, 0);
        if (total > 0) return true;
    }

    if (Array.isArray(payload.special_deductions)) {
        const total = payload.special_deductions.reduce(function (sum, item) {
            return sum + (Number(item.amount) || 0);
        }, 0);
        if (total > 0) return true;
    }

    if (Array.isArray(payload.nolco)) {
        const total = payload.nolco.reduce(function (sum, row) {
            return sum +
                (Number(row.a) || 0) +
                (Number(row.b) || 0) +
                (Number(row.c) || 0) +
                (Number(row.d) || 0);
        }, 0);
        if (total > 0) return true;
    }

    return false;
}

async function saveComputation() {
    if (!dom.bestScheme) {
        return;
    }

    try {
        const payload = getFormState();

        // Reject empty submissions before touching the
        // network.
        if (!hasAnyInput(payload)) {
            showToast(
                "warning",
                "Nothing to save",
                "Please enter at least one income or deduction " +
                "amount before saving the computation."
            );
            return;
        }

        const response = await saveTax(payload);
        renderResults(response.results, dom);
        updateCostDisplay();

        if (response.duplicate) {
            showToast(
                "warning",
                "Already saved",
                "A computation with the same values was saved in " +
                "the last 5 minutes. It was saved again to your " +
                "history."
            );
        } else {
            showToast(
                "success",
                window.templateSourceId
                    ? "New computation saved"
                    : "Computation saved",
                window.templateSourceId
                    ? "The original computation was left unchanged."
                    : "Your computation was saved to history."
            );
        }

        // Return to the dashboard after a successful save so the
        // newly saved computation appears in the recent-computations list.
        window.location.assign("/dashboard");

    } catch (error) {
        showToast(
            "error",
            "Save failed",
            error && error.message
                ? error.message
                : "Could not save the computation."
        );
    }
}

function resetForm() {
    const confirmed = window.confirm(
        "Reset the form? All unsaved input will be cleared."
    );

    if (confirmed) {
        window.location.reload();
    }
}

function resetFormSilently() {
    const metadataInputs = [
        document.getElementById("computationTitle"),
        document.getElementById("computationNote")
    ];

    metadataInputs.forEach(function (input) {
        if (input) {
            input.value = "";
        }
    });

    const staticInputs = [
        dom.grossComp,
        dom.nonTaxComp,
        dom.cashSales,
        dom.accrualSales,
        dom.cashCost,
        dom.accrualCost
    ];

    staticInputs.forEach(function (input) {
        if (input) {
            input.value = "0";
        }
    });

    dom.taxpayerRadios.forEach(function (radio) {
        radio.checked = radio.value === "pure";
    });

    if (dom.compensationSection) {
        dom.compensationSection.classList.add("hidden");
    }

    if (dom.otherIncomeList) {
        dom.otherIncomeList.innerHTML = "";
        appendOtherIncomeRow(
            dom.otherIncomeList,
            buildRowHandlers(),
            "Other Income 1",
            0
        );
        appendOtherIncomeRow(
            dom.otherIncomeList,
            buildRowHandlers(),
            "Other Income 2",
            0
        );
    }

    if (dom.specialDeductions) {
        dom.specialDeductions.innerHTML = "";
        appendSpecialDeductionRow(
            dom.specialDeductions,
            buildRowHandlers()
        );
    }

    if (dom.nolcoTableBody) {
        dom.nolcoTableBody.innerHTML = "";
        for (let i = 0; i < 4; i += 1) {
            appendNolcoRow(dom.nolcoTableBody, buildRowHandlers());
        }
        recomputeNolco(dom.nolcoTableBody, dom.totalNolcoD);
    }

    document
        .querySelectorAll(".ordinary-deduction")
        .forEach(function (input) {
            input.value = "0";
        });

    const emptyRow =
        '<div class="compute-row">' +
        "<span>Enter your income to compute</span>" +
        '<span class="amount">PHP 0.00</span>' +
        "</div>";

    if (dom.osdResult) {
        dom.osdResult.innerHTML = emptyRow;
    }

    if (dom.itemizedResult) {
        dom.itemizedResult.innerHTML = emptyRow;
    }

    if (dom.eightResult) {
        dom.eightResult.innerHTML = emptyRow;
    }

    if (dom.bestScheme) {
        dom.bestScheme.textContent =
            "Enter income and deduction values to see the " +
            "recommended tax scheme.";
    }

    [dom.osdCard, dom.itemizedCard, dom.eightCard].forEach(
        function (card) {
            if (card) {
                card.classList.remove("is-best");
            }
        }
    );

    updateCostDisplay();
}

/* ============================================================
   PUBLIC ATTACH FUNCTION
   ============================================================ */

export function attachEvents(domRefs) {
    dom = domRefs;

    autoCompute = debounce(computeOnly, AUTO_COMPUTE_DELAY);

    dom.taxpayerRadios.forEach(function (radio) {
        radio.addEventListener("change", function () {
            syncCompensationVisibility();
            autoCompute();
        });
    });

    const staticInputs = [
        dom.grossComp,
        dom.nonTaxComp,
        dom.cashSales,
        dom.accrualSales,
        dom.cashCost,
        dom.accrualCost
    ];

    staticInputs.forEach(function (input) {
        if (input) {
            input.addEventListener("input", autoCompute);
        }
    });

    document.addEventListener("input", function (event) {
        const target = event.target;

        if (!target || !target.classList) {
            return;
        }

        if (target.dataset &&
            target.dataset.setting === "percentage_tax_rate") {
            document
                .querySelectorAll('[data-setting="percentage_tax_rate"]')
                .forEach(function (input) {
                    if (input !== target) {
                        input.value = target.value;
                    }
                });
        }

        if (target.classList.contains("setting-input")) {
            target.dataset.userModified = "true";
        }

        const dynamicClasses = [
            "ordinary-deduction",
            "other-income",
            "special-deduction",
            "nolco-a",
            "nolco-b",
            "nolco-c",
            "nolco-d",
            "setting-input"
        ];

        const isDynamic = dynamicClasses.some(function (cls) {
            return target.classList.contains(cls);
        });

        if (isDynamic) {
            autoCompute();
        }
    });


    // Modal for viewing BIR Tax Table from Step 4
    const openModalBtn = document.getElementById("openTaxTableModalBtn");
    const modalOverlay = document.getElementById("taxTableModal");
    const closeModalBtn = document.getElementById("closeTaxTableModalBtn");
    const closeModalFooterBtn = document.getElementById("closeTaxTableModalFooterBtn");

    if (openModalBtn && modalOverlay) {
        openModalBtn.addEventListener("click", async function () {
            modalOverlay.style.display = "flex";

            // Reload on every open so edits saved in the tax-table manager
            // are reflected without requiring the calculator page to reload.
            try {
                const taxTable = await fetchTaxTable();
                renderTaxTableModal(taxTable.brackets);
            } catch (error) {
                // Keep the server-rendered table visible if the refresh fails.
            }
        });
    }
    [closeModalBtn, closeModalFooterBtn].forEach(function (btn) {
        if (btn && modalOverlay) {
            btn.addEventListener("click", function () {
                modalOverlay.style.display = "none";
            });
        }
    });
    if (modalOverlay) {
        modalOverlay.addEventListener("click", function (e) {
            if (e.target === modalOverlay) {
                modalOverlay.style.display = "none";
            }
        });
    }

    const handlers = buildRowHandlers();

    document
        .querySelectorAll('[data-action="add-other-income"]')
        .forEach(function (button) {
            button.addEventListener("click", function () {
                appendOtherIncomeRow(dom.otherIncomeList, handlers);
                autoCompute();
            });
        });

    document
        .querySelectorAll('[data-action="add-special-deduction"]')
        .forEach(function (button) {
            button.addEventListener("click", function () {
                appendSpecialDeductionRow(dom.specialDeductions, handlers);
                autoCompute();
            });
        });

    document
        .querySelectorAll('[data-action="add-nolco-row"]')
        .forEach(function (button) {
            button.addEventListener("click", function () {
                appendNolcoRow(dom.nolcoTableBody, handlers);
                autoCompute();
            });
        });

    document
        .querySelectorAll('[data-action="save-computation"]')
        .forEach(function (button) {
            button.addEventListener("click", saveComputation);
        });

    document
        .querySelectorAll('[data-action="reset-form"]')
        .forEach(function (button) {
            button.addEventListener("click", resetForm);
        });

    syncCompensationVisibility();
    updateCostDisplay();
}

export function getRowHandlers() {
    return buildRowHandlers();
}

export { updateCostDisplay, AUTO_COMPUTE_DELAY };
