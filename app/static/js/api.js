/* ============================================================
   API MODULE
   ============================================================
   Wraps the calls to the backend JSON endpoints.

     POST /api/compute    compute without saving
     POST /api/save       compute and save
     GET  /api/history    list saved computations

   Only this module talks to the network. This keeps the
   rest of the client code free of fetch calls.
   ============================================================ */

/**
 * Custom error type for API failures.
 */
export class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

/**
 * Internal helper that posts a payload to the given URL
 * and parses the JSON response.
 */
async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    let data = null;
    try {
        data = await response.json();
    } catch (err) {
        data = null;
    }

    if (!response.ok) {
        const message =
            (data && data.error) ||
            "The server could not complete the request.";
        throw new ApiError(message, response.status);
    }

    return data;
}

/**
 * Compute the tax without saving anything.
 *
 * Safe to call on every keystroke because it never writes
 * to the database.
 *
 * @param {Object} payload
 * @returns {Promise<Object>} The results object.
 */
export async function computeTax(payload) {
    return postJson("/api/compute", payload);
}

/**
 * Compute the tax and save it to the user's history.
 *
 * @param {Object} payload
 * @returns {Promise<Object>} The response with id, results,
 *     and duplicate flag.
 */
export async function saveTax(payload) {
    return postJson("/api/save", payload);
}

/**
 * Fetch the current user's saved computations.
 *
 * @returns {Promise<Array<Object>>}
 */
export async function fetchHistory() {
    const response = await fetch("/api/history", {
        method: "GET",
        headers: {
            "Accept": "application/json"
        }
    });

    if (!response.ok) {
        throw new ApiError(
            "Could not load history.",
            response.status
        );
    }

    return response.json();
}