/**
 * moxfieldCollection.js
 * ----------------------
 * Port of test/normalize.py's normalize_collection() -- no behavior
 * change. This is the adapter layer: it turns Moxfield's real raw
 * collection API response (paginated, one record per physical card
 * instance, deeply nested Scryfall-style card objects) into the flat
 * {name, total_quantity, unique_printings} shape that
 * src/engine_js/collection.js's buildCollectionIndex() expects.
 *
 * This is deliberately separate from src/engine_js/. The engine
 * assumes it's already been handed clean, normalized data -- it has
 * no idea Moxfield's API even exists. This module is the one place
 * that knows about Moxfield's real response shape, so if that shape
 * ever changes, only this file needs to change.
 *
 * Real raw record shape (one entry from a collection API page's
 * `data` array):
 *
 *   {
 *     id, quantity, condition, game, finish, isFoil, isAlter,
 *     isProxy, isPrefPrinting, tradeBinder, language,
 *     card: {
 *       name, set, cn, scryfall_id, prices: {...}, ...many more fields
 *     }
 *   }
 *
 * Multiple raw records can represent the same printing (e.g. copies
 * added at different times, or across trade binders) -- those are
 * combined and their quantities summed, exactly as normalize.py does.
 */

/**
 * @typedef {Object} NormalizedPrinting
 * @property {string|null} set
 * @property {string|null} collectorNumber
 * @property {string|null} finish
 * @property {number} quantity
 * @property {string|null} scryfallId
 */

/**
 * @typedef {Object} NormalizedCard
 * @property {string} name
 * @property {number} totalQuantity
 * @property {NormalizedPrinting[]} uniquePrintings
 */

/**
 * Normalize raw Moxfield collection records into:
 *
 *   CARD
 *   |- name
 *   |- total quantity
 *   `- unique printings
 *        |- set
 *        |- collector number
 *        |- finish
 *        |- quantity
 *        `- scryfall id
 *
 * Records representing the same printing are combined and their
 * quantities summed.
 *
 * @param {Array<object>} records - raw records from a collection API
 *   page's `data` array (or records concatenated across all pages).
 * @returns {NormalizedCard[]}
 */
function normalizeCollection(records) {
  const cardsByName = new Map();

  for (const record of records) {
    const card = record.card;
    if (!card) {
      throw new Error(`Collection record ${record.id} does not contain a card object.`);
    }

    const name = card.name;
    if (!name) {
      throw new Error(`Collection record ${record.id} does not contain a card name.`);
    }

    const setCode = card.set ?? null;
    const collectorNumber = card.cn ?? null;
    const finish = record.finish ?? null;
    const scryfallId = card.scryfall_id ?? null;

    let quantity = record.quantity;
    if (quantity === null || quantity === undefined) quantity = 0;
    if (typeof quantity !== "number" || !Number.isFinite(quantity)) {
      throw new Error(`Invalid quantity for collection record ${record.id}: ${JSON.stringify(quantity)}`);
    }

    if (!cardsByName.has(name)) {
      cardsByName.set(name, {
        name,
        totalQuantity: 0,
        printingsByKey: new Map(),
      });
    }

    const normalizedCard = cardsByName.get(name);
    normalizedCard.totalQuantity += quantity;

    // Set + collector number + finish + scryfall id together identify
    // the normalized printing.
    const printingKey = JSON.stringify([setCode, collectorNumber, finish, scryfallId]);

    if (!normalizedCard.printingsByKey.has(printingKey)) {
      normalizedCard.printingsByKey.set(printingKey, {
        set: setCode,
        collectorNumber,
        finish,
        quantity: 0,
        scryfallId,
      });
    }

    const printing = normalizedCard.printingsByKey.get(printingKey);
    printing.quantity += quantity;
  }

  const normalized = [];
  for (const card of cardsByName.values()) {
    normalized.push({
      name: card.name,
      totalQuantity: card.totalQuantity,
      uniquePrintings: Array.from(card.printingsByKey.values()),
    });
  }

  // Sort cards alphabetically for deterministic output.
  normalized.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

  // Sort printings deterministically as well.
  for (const card of normalized) {
    card.uniquePrintings.sort((a, b) => {
      const keyA = [a.set, a.collectorNumber, a.finish, a.scryfallId].map((x) => String(x).toLowerCase());
      const keyB = [b.set, b.collectorNumber, b.finish, b.scryfallId].map((x) => String(x).toLowerCase());
      for (let i = 0; i < keyA.length; i++) {
        if (keyA[i] < keyB[i]) return -1;
        if (keyA[i] > keyB[i]) return 1;
      }
      return 0;
    });
  }

  return normalized;
}

/**
 * Convert the JS-shaped NormalizedCard[] (camelCase, as produced by
 * normalizeCollection) into the exact snake_case shape the engine's
 * buildCollectionIndex() expects (matching collection_normalized.json
 * / the Python engine's contract).
 *
 * @param {NormalizedCard[]} normalized
 * @returns {Array<object>}
 */
function toEngineCollectionFormat(normalized) {
  return normalized.map((card) => ({
    name: card.name,
    total_quantity: card.totalQuantity,
    unique_printings: card.uniquePrintings.map((p) => ({
      set: p.set,
      collector_number: p.collectorNumber,
      finish: p.finish,
      quantity: p.quantity,
      scryfall_id: p.scryfallId,
    })),
  }));
}

/**
 * Validate that normalization preserved the complete quantity
 * represented by the raw collection. Raw records may contain multiple
 * records for the same printing, so validation is done via quantity
 * totals, not record counts.
 *
 * Throws on any mismatch, exactly as normalize.py's
 * validate_normalized_collection() does.
 *
 * @param {Array<object>} rawRecords
 * @param {NormalizedCard[]} normalizedCards
 */
function validateNormalizedCollection(rawRecords, normalizedCards) {
  const rawQuantity = rawRecords.reduce((sum, r) => sum + (r.quantity || 0), 0);
  const normalizedQuantity = normalizedCards.reduce((sum, c) => sum + c.totalQuantity, 0);

  if (rawQuantity !== normalizedQuantity) {
    throw new Error(
      `Normalized quantity (${normalizedQuantity}) does not match raw quantity (${rawQuantity}).`
    );
  }

  for (const card of normalizedCards) {
    const printingQuantity = card.uniquePrintings.reduce((sum, p) => sum + p.quantity, 0);
    if (printingQuantity !== card.totalQuantity) {
      throw new Error(
        `Quantity mismatch for card '${card.name}': card total is ${card.totalQuantity}, ` +
          `but printing total is ${printingQuantity}.`
      );
    }
  }
}

module.exports = { normalizeCollection, toEngineCollectionFormat, validateNormalizedCollection };
