/* ============================================================
   UTILS MODULE
   ============================================================
   Pure utility functions with no dependencies. Safe to
   import from any other module in the calculator.
   ============================================================ */

/**
 * Parse a formatted number string into a float.
 *
 * Accepts values that contain commas, peso signs, or
 * whitespace. Returns 0 if parsing fails.
 *
 * @param {*} value - Any value that may represent a number.
 * @returns {number} The parsed number, or 0 on failure.
 */
export function parseNumber(value) {
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

/**
 * Format a number with thousand separators and two decimal
 * places. Used for input field display.
 *
 * @param {*} value - Any value that may represent a number.
 * @returns {string} The formatted number, e.g. "1,234.50".
 */
export function formatNumber(value) {
    const number = parseNumber(value);
    return number.toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Format a number as a peso string with the PHP prefix.
 * Used for computed results.
 *
 * @param {*} value - Any value that may represent a number.
 * @returns {string} The formatted peso string.
 */
export function formatPeso(value) {
    return "PHP " + formatNumber(value);
}

/**
 * Attach a live input formatter to a text input so that the
 * displayed value uses thousand separators as the user
 * types. The stored value remains a plain number once it is
 * parsed.
 *
 * Also clears the initial "0" when the input gains focus,
 * so the user does not have to delete it manually.
 *
 * @param {HTMLInputElement} input - The input element.
 */
export function attachInputFormatter(input) {
    if (!input) {
        return;
    }

    // Clear the default zero when the field is focused.
    input.addEventListener("focus", function () {
        if (this.value === "0" || this.value === "0.00") {
            this.value = "";
        }
        this.select();
    });

    // Restore a "0" if the user leaves the field empty.
    input.addEventListener("blur", function () {
        if (this.value.trim() === "") {
            this.value = "0";
        }
    });

    input.addEventListener("input", function () {
        const cursorPosition = this.selectionStart;
        const originalLength = this.value.length;

        // Strip everything except digits and a single dot.
        let raw = this.value.replace(/[^\d.]/g, "");

        // Collapse multiple dots into one.
        const parts = raw.split(".");
        if (parts.length > 2) {
            raw = parts[0] + "." + parts.slice(1).join("");
        }

        // Rebuild the formatted value.
        const hasDot = raw.includes(".");
        const integerPart = raw.split(".")[0] || "0";
        const decimalPart = hasDot ? "." + (raw.split(".")[1] || "") : "";

        this.value =
            parseFloat(integerPart).toLocaleString("en-US") +
            decimalPart;

        // Restore the cursor position as best as possible.
        const newLength = this.value.length;
        const delta = newLength - originalLength;
        this.setSelectionRange(
            cursorPosition + delta,
            cursorPosition + delta
        );
    });
}

/**
 * Debounce a function so that it only runs after the given
 * delay has elapsed since the last call. Used to limit the
 * frequency of API calls while the user is typing.
 *
 * @param {Function} fn - The function to debounce.
 * @param {number} delay - Delay in milliseconds.
 * @returns {Function} The debounced function.
 */
export function debounce(fn, delay) {
    let timer = null;

    return function (...args) {
        if (timer) {
            clearTimeout(timer);
        }

        timer = setTimeout(() => {
            fn.apply(this, args);
        }, delay);
    };
}