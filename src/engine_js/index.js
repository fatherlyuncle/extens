/**
 * index.js
 * --------
 * Deck-cost engine (JS port): UI-independent core for the Moxfield
 * deck-cost extension.
 *
 * Public API:
 *
 *   const { calculateDeckCost } = require("./engine_js");
 *   const result = calculateDeckCost({
 *     collection, normalizedDeck, rawDeck, pricingStrategy: "cheapest"
 *   });
 *
 * See engine.js for the full calculateDeckCost() docstring, including
 * the two deliberate deviations carried over from the Python version.
 *
 * Money fields on the result (costCents, unitPriceCents, lineTotalCents)
 * are integer CENTS, not dollars -- use util.formatCents() to display.
 */

const { calculateDeckCost } = require("./engine");
const { formatCents } = require("./util");

module.exports = { calculateDeckCost, formatCents };
