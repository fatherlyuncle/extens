/**
 * engine.js
 * ---------
 * Public orchestration layer for the deck-cost engine (JS port).
 *
 * This mirrors src/engine/engine.py exactly, including its two
 * deliberate deviations from a naive single-"deck"-argument design:
 *
 * 1. Two "deck" inputs, not one.
 *    normalizedDeck carries card names/quantities/board; rawDeck
 *    carries printing/price metadata. They're separate arguments
 *    because deck_cost.py always needed both -- collapsing them into
 *    one "deck" argument would mean guessing which shape the caller
 *    actually has.
 *
 * 2. includeCommander is a manual override, not a read of Moxfield's
 *    own `includeCommandersInPrice` flag.
 *
 *    The raw deck JSON does carry an includeCommandersInPrice field
 *    (false in the reference fixture), but deck_cost.py never read it
 *    -- it always counted the commander as required. includeCommander
 *    defaults to true here specifically to reproduce that behavior.
 *    It does NOT read rawDeck.includeCommandersInPrice. Wiring that up
 *    is a separate, deliberate decision (it would change required from
 *    100 to 99 for the reference fixture).
 *
 * Money is returned as integer costCents/unitPriceCents/lineTotalCents,
 * not floating-point dollars -- see util.js.
 */

const { buildCollectionIndex } = require("./collection");
const { buildRequirements, extractDeckRecords } = require("./deck");
const { matchDeck } = require("./matching");
const { buildRawPriceCatalog, selectPrice } = require("./pricing");

/**
 * Calculate the cost to complete a deck given a collection.
 *
 * @param {object} params
 * @param {Array<object>} params.collection - normalized collection data.
 * @param {object} params.normalizedDeck - normalized deck data (dict
 *   with "commander"/"mainboard" arrays).
 * @param {object} params.rawDeck - raw Moxfield deck API response
 *   (dict with a "boards" object), used for printing/price metadata.
 * @param {"same"|"cheapest"|"most_expensive"} [params.pricingStrategy="cheapest"]
 * @param {boolean} [params.includeCommander=true]
 * @returns {import('./models').DeckCostResult}
 */
function calculateDeckCost({
  collection,
  normalizedDeck,
  rawDeck,
  pricingStrategy = "cheapest",
  includeCommander = true,
}) {
  const collectionIndex = buildCollectionIndex(collection);
  const requirements = buildRequirements(normalizedDeck, includeCommander);
  const matches = matchDeck(requirements, collectionIndex);

  const required = matches.reduce((sum, m) => sum + m.required, 0);
  const owned = matches.reduce((sum, m) => sum + m.owned, 0);
  const missing = matches.reduce((sum, m) => sum + m.missing, 0);

  const rawRecords = extractDeckRecords(rawDeck);
  const catalog = buildRawPriceCatalog(rawRecords);

  let costCents = 0;
  let pricedQuantity = 0;
  let unpricedQuantity = 0;
  const selections = [];

  for (const match of matches) {
    const missingQty = match.missing;
    if (missingQty <= 0) continue;

    const name = match.name;
    const selected = selectPrice(catalog.get(name) || [], pricingStrategy);

    if (selected === null) {
      unpricedQuantity += missingQty;
      continue;
    }

    const record = selected.record;
    const unitPriceCents = selected.priceCents;
    const lineTotalCents = unitPriceCents * missingQty;

    costCents += lineTotalCents;
    pricedQuantity += missingQty;

    selections.push({
      cardName: name,
      setCode: String(record.set ?? "?"),
      collectorNumber: String(record.cn ?? "?"),
      finish: selected.finish,
      priceField: selected.priceField,
      unitPriceCents,
      quantity: missingQty,
      lineTotalCents,
    });
  }

  return {
    required,
    owned,
    missing,
    pricedQuantity,
    unpricedQuantity,
    costCents,
    selections,
  };
}

module.exports = { calculateDeckCost };
