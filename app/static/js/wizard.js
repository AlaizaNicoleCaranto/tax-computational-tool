/* ============================================================
   WIZARD MODULE
   ============================================================
   Handles step navigation for the calculator. Each step is
   a container with class "wizard-step" and a data-step
   attribute. Only one step is visible at a time.

   Navigation is controlled by:
     - The step indicator buttons in the wizard nav
     - The Back and Next buttons in the wizard actions bar

   The module also disables the Back button on the first
   step and the Next button on the last step.
   ============================================================ */

const TOTAL_STEPS = 4;

let currentStep = 1;

/**
 * Return an array of every step container on the page.
 */
function getStepContainers() {
    return document.querySelectorAll(".wizard-step");
}

/**
 * Return an array of every step indicator button.
 */
function getStepButtons() {
    return document.querySelectorAll(".wizard-step-btn");
}

/**
 * Show the step with the given number and hide the others.
 *
 * @param {number} stepNumber - The step to activate.
 */
function showStep(stepNumber) {
    // Clamp the step number to the valid range.
    if (stepNumber < 1) {
        stepNumber = 1;
    }
    if (stepNumber > TOTAL_STEPS) {
        stepNumber = TOTAL_STEPS;
    }

    currentStep = stepNumber;

    // Toggle the active class on each step container.
    getStepContainers().forEach(function (container) {
        const step = parseInt(container.dataset.step, 10);
        container.classList.toggle("active", step === stepNumber);
    });

    // Update the step indicator buttons.
    getStepButtons().forEach(function (button) {
        const step = parseInt(button.dataset.step, 10);

        button.classList.toggle("active", step === stepNumber);
        button.classList.toggle("completed", step < stepNumber);
    });

    // Update the Back and Next buttons.
    updateNavigationButtons();

    // Scroll to the top of the page so that the user sees
    // the new step from the beginning.
    window.scrollTo({ top: 0, behavior: "smooth" });
}

/**
 * Enable or disable the Back and Next buttons based on the
 * current step.
 */
function updateNavigationButtons() {
    const backButton = document.querySelector(
        '[data-action="wizard-back"]'
    );
    const nextButton = document.querySelector(
        '[data-action="wizard-next"]'
    );

    if (backButton) {
        backButton.disabled = currentStep === 1;
    }

    if (nextButton) {
        nextButton.disabled = currentStep === TOTAL_STEPS;
    }
}

/**
 * Advance to the next step.
 */
function goNext() {
    if (currentStep < TOTAL_STEPS) {
        showStep(currentStep + 1);
    }
}

/**
 * Go back to the previous step.
 */
function goBack() {
    if (currentStep > 1) {
        showStep(currentStep - 1);
    }
}

/**
 * Attach all wizard navigation event listeners.
 */
export function initializeWizard() {
    // Step indicator buttons.
    getStepButtons().forEach(function (button) {
        button.addEventListener("click", function () {
            const step = parseInt(this.dataset.step, 10);
            showStep(step);
        });
    });

    // Back and Next buttons.
    document
        .querySelectorAll('[data-action="wizard-back"]')
        .forEach(function (button) {
            button.addEventListener("click", goBack);
        });

    document
        .querySelectorAll('[data-action="wizard-next"]')
        .forEach(function (button) {
            button.addEventListener("click", goNext);
        });

    // Initialize on the first step.
    showStep(1);
}

/**
 * Jump to a specific step from outside the module.
 *
 * @param {number} stepNumber
 */
export function goToStep(stepNumber) {
    showStep(stepNumber);
}