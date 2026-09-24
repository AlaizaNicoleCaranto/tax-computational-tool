/* ============================================================
   TOAST MODULE
   ============================================================
   Provides a lightweight notification system. Toasts appear
   in the top-right corner, stack vertically, and disappear
   after a short delay.

   Usage:
       import { showToast } from "./toast.js";
       showToast("success", "Saved!", "Your computation was saved.");
       showToast("warning", "Duplicate", "This was already saved.");
       showToast("error", "Failed", "Could not save the data.");
   ============================================================ */

const DEFAULT_DURATION = 4500;

// Container is created lazily on first use so the module can
// be imported before the DOM is ready.
let container = null;

/**
 * Ensure the toast container exists in the DOM.
 */
function ensureContainer() {
    if (container && document.body.contains(container)) {
        return container;
    }

    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);

    return container;
}

/**
 * Choose an icon character based on the toast variant.
 */
function iconForVariant(variant) {
    switch (variant) {
        case "success":
            return "\u2713"; // check mark
        case "warning":
            return "\u26A0"; // warning sign
        case "error":
            return "\u2717"; // ballot X
        default:
            return "\u2139"; // information
    }
}

/**
 * Show a toast notification.
 *
 * @param {string} variant - "success", "warning", or "error".
 * @param {string} title - Short headline.
 * @param {string} [message] - Optional supporting text.
 * @param {number} [duration] - Milliseconds before auto dismiss.
 */
export function showToast(variant, title, message, duration) {
    const host = ensureContainer();
    const timeout = duration || DEFAULT_DURATION;

    const toast = document.createElement("div");
    toast.className = "toast " + (variant || "success");

    // Icon
    const icon = document.createElement("span");
    icon.className = "toast-icon";
    icon.textContent = iconForVariant(variant);

    // Content
    const content = document.createElement("div");
    content.className = "toast-content";

    const titleEl = document.createElement("div");
    titleEl.className = "toast-title";
    titleEl.textContent = title || "";

    content.appendChild(titleEl);

    if (message) {
        const messageEl = document.createElement("div");
        messageEl.className = "toast-message";
        messageEl.textContent = message;
        content.appendChild(messageEl);
    }

    // Close button
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "toast-close";
    closeBtn.textContent = "\u00D7";
    closeBtn.setAttribute("aria-label", "Close notification");

    // Assemble
    toast.appendChild(icon);
    toast.appendChild(content);
    toast.appendChild(closeBtn);

    // Dismissal logic
    function dismiss() {
        toast.classList.add("removing");
        setTimeout(function () {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    closeBtn.addEventListener("click", dismiss);

    host.appendChild(toast);

    // Auto dismiss
    setTimeout(dismiss, timeout);
}