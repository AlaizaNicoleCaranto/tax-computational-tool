/* ============================================================
   DYNAMIC ROWS MODULE
   ============================================================
   Creates and manages the dynamic rows used by three
   sections of the calculator:

     - Other non-operating income
     - Special allowable itemized deductions
     - Net Operating Loss Carry Over (NOLCO) schedule

   Each row type has its own builder. The module exposes
   append functions that the events module calls when the
   user clicks the corresponding add button.
   ============================================================ */

import {
    attachInputFormatter,
    formatNumber,
    formatPeso,
    parseNumber
} from "./utils.js";

/* ============================================================
   OTHER INCOME
   ============================================================ */

function createOtherIncomeRow(title, amount, onRemove, onChange) {
    const row = document.createElement("div");
    row.className = "dynamic-row";

    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.className = "other-income-title";
    titleInput.value = title || "";
    titleInput.placeholder = "Description";

    const amountWrapper = document.createElement("div");
    amountWrapper.className = "input-box";

    const prefix = document.createElement("span");
    prefix.className = "prefix";
    prefix.textContent = "PHP";

    const amountInput = document.createElement("input");
    amountInput.type = "text";
    amountInput.className = "other-income";
    amountInput.value = formatNumber(amount || 0);
    amountInput.inputMode = "decimal";

    amountWrapper.appendChild(prefix);
    amountWrapper.appendChild(amountInput);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-btn";
    removeButton.textContent = "\u00D7";
    removeButton.addEventListener("click", function () {
        row.remove();
        if (typeof onRemove === "function") {
            onRemove();
        }
    });

    attachInputFormatter(amountInput);

    if (typeof onChange === "function") {
        amountInput.addEventListener("input", onChange);
    }

    row.appendChild(titleInput);
    row.appendChild(amountWrapper);
    row.appendChild(removeButton);

    return row;
}

export function appendOtherIncomeRow(container, handlers, title, amount) {
    if (!container) {
        return;
    }

    const defaultTitle =
        title || "Other Income " + (container.children.length + 1);

    const row = createOtherIncomeRow(
        defaultTitle,
        amount || 0,
        handlers.onRemove,
        handlers.onChange
    );

    container.appendChild(row);
}

/* ============================================================
   SPECIAL DEDUCTIONS
   ============================================================ */

function createSpecialDeductionRow(title, amount, onRemove, onChange) {
    const row = document.createElement("div");
    row.className = "dynamic-row";

    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.className = "special-title";
    titleInput.value = title || "";
    titleInput.placeholder = "Title of the deduction";

    const amountWrapper = document.createElement("div");
    amountWrapper.className = "input-box";

    const prefix = document.createElement("span");
    prefix.className = "prefix";
    prefix.textContent = "PHP";

    const amountInput = document.createElement("input");
    amountInput.type = "text";
    amountInput.className = "special-deduction";
    amountInput.value = formatNumber(amount || 0);
    amountInput.inputMode = "decimal";

    amountWrapper.appendChild(prefix);
    amountWrapper.appendChild(amountInput);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "remove-btn";
    removeButton.textContent = "\u00D7";
    removeButton.addEventListener("click", function () {
        row.remove();
        if (typeof onRemove === "function") {
            onRemove();
        }
    });

    attachInputFormatter(amountInput);

    if (typeof onChange === "function") {
        amountInput.addEventListener("input", onChange);
    }

    row.appendChild(titleInput);
    row.appendChild(amountWrapper);
    row.appendChild(removeButton);

    return row;
}

export function appendSpecialDeductionRow(container, handlers, title, amount) {
    if (!container) {
        return;
    }

    const row = createSpecialDeductionRow(
        title || "",
        amount || 0,
        handlers.onRemove,
        handlers.onChange
    );

    container.appendChild(row);
}

/* ============================================================
   NOLCO SCHEDULE
   ============================================================ */

function computeNolcoE(row) {
    const a = parseNumber(row.querySelector(".nolco-a").value);
    const b = parseNumber(row.querySelector(".nolco-b").value);
    const c = parseNumber(row.querySelector(".nolco-c").value);
    const d = parseNumber(row.querySelector(".nolco-d").value);

    return Math.max(0, a - (b + c + d));
}

export function recomputeNolco(tableBody, totalCell) {
    if (!tableBody) {
        return 0;
    }

    let totalD = 0;

    tableBody.querySelectorAll("tr").forEach(function (row) {
        const e = computeNolcoE(row);
        const eInput = row.querySelector(".nolco-e");
        if (eInput) {
            eInput.value = formatPeso(e);
        }

        const dInput = row.querySelector(".nolco-d");
        if (dInput) {
            totalD += parseNumber(dInput.value);
        }
    });

    if (totalCell) {
        totalCell.textContent = formatPeso(totalD);
    }

    return totalD;
}

function createNolcoRow(handlers) {
    const row = document.createElement("tr");

    function makeCell(className, options) {
        const cell = document.createElement("td");
        const input = document.createElement("input");
        input.type = "text";
        input.className = className;

        if (options && options.year) {
            input.placeholder = "YYYY";
            input.classList.add("year-input");
            input.inputMode = "numeric";
            input.addEventListener("input", handlers.onChange);
        } else if (options && options.readonly) {
            input.readOnly = true;
            input.value = "PHP 0.00";
        } else {
            input.value = "0";
            input.inputMode = "decimal";
            attachInputFormatter(input);
            input.addEventListener("input", function () {
                if (typeof handlers.onNolcoChange === "function") {
                    handlers.onNolcoChange();
                }
            });
        }

        cell.appendChild(input);
        return cell;
    }

    row.appendChild(makeCell("year-input", { year: true }));
    row.appendChild(makeCell("nolco-a", {}));
    row.appendChild(makeCell("nolco-b", {}));
    row.appendChild(makeCell("nolco-c", {}));
    row.appendChild(makeCell("nolco-d", {}));
    row.appendChild(makeCell("nolco-e", { readonly: true }));

    return row;
}

export function appendNolcoRow(tableBody, handlers) {
    if (!tableBody) {
        return;
    }

    const row = createNolcoRow(handlers);
    tableBody.appendChild(row);
}