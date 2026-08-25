/**
 * deck.js
 * -------
 * Port of src/engine/deck.py -- no behavior change.
 *
 * extractRawBoardCards / extractDeckRecords are direct translations of
 * the Python originals. buildRequirements carries the same
 * includeCommander flag and board field as the Python version -- see
 * engine.js for the note on why that flag doesn't read Moxfield's own
 * includeCommandersInPrice field yet.
 */

const { qty } = require("./util");

// ---------------------------------------------------------------------
// NORMALIZED DECK
// ---------------------------------------------------------------------

/**
 * Return commander + mainboard records; deliberately excludes sideboard.
 * @param {object} deck
 * @returns {Array<object>}
 */
function normalizedDeckRecords(deck) {
  const records = [];
  for (const section of ["commander", "mainboard"]) {
    const value = deck[section];
    if (Array.isArray(value)) {
      for (const x of value) {
        if (x !== null && typeof x === "object") records.push(x);
      }
    }
  }
  return records;
}

/**
 * Build the list of CardRequirement objects the matcher needs.
 *
 * includeCommander=true (the default) reproduces deck_cost.py's
 * original, unconditional behavior of counting the commander as
 * required. Setting it false excludes commander records entirely.
 *
 * @param {object} normalizedDeck
 * @param {boolean} [includeCommander=true]
 * @returns {import('./models').CardRequirement[]}
 */
function buildRequirements(normalizedDeck, includeCommander = true) {
  const sections = includeCommander ? ["commander", "mainboard"] : ["mainboard"];

  const requirements = [];
  for (const section of sections) {
    const value = normalizedDeck[section];
    if (!Array.isArray(value)) continue;
    for (const record of value) {
      if (record === null || typeof record !== "object" || !record.name) continue;
      requirements.push({
        name: String(record.name),
        quantity: qty(record),
        board: section,
        finish: record.finish || "nonFoil",
        scryfallId: record.scryfall_id ?? null,
      });
    }
  }
  return requirements;
}

// ---------------------------------------------------------------------
// RAW MOXFIELD DECK
// ---------------------------------------------------------------------

/**
 * Raw Moxfield board shape:
 *
 *   {
 *     count: 99,
 *     cards: {
 *       "internal-id": {
 *         quantity: 1,
 *         boardType: "mainboard",
 *         finish: "nonFoil",
 *         card: {...}
 *       }
 *     }
 *   }
 *
 * Flatten each nested card into a convenient record while preserving
 * the board-specific quantity/finish fields.
 * @param {object} board
 * @returns {Array<object>}
 */
function extractRawBoardCards(board) {
  if (board === null || typeof board !== "object") return [];

  const cards = board.cards;
  let entries;
  if (cards !== null && typeof cards === "object" && !Array.isArray(cards)) {
    entries = Object.values(cards);
  } else if (Array.isArray(cards)) {
    entries = cards;
  } else {
    return [];
  }

  const result = [];

  for (const entry of entries) {
    if (entry === null || typeof entry !== "object") continue;

    const card = entry.card;
    if (card === null || typeof card !== "object") continue;

    const record = { ...card };
    record.quantity = qty(entry);
    record.finish = entry.finish ?? card.defaultFinish ?? "nonFoil";
    record.boardType = entry.boardType;
    record.isFoil = Boolean(entry.isFoil);
    record.isAlter = Boolean(entry.isAlter);
    record.isProxy = Boolean(entry.isProxy);
    result.push(record);
  }

  return result;
}

/**
 * Extract the actual Commander deck from a raw Moxfield response.
 *
 * IMPORTANT:
 *   raw Moxfield does NOT use top-level "commander"/"mainboard".
 *   It uses:
 *
 *       rawDeck.boards.commanders.cards
 *       rawDeck.boards.mainboard.cards
 *
 *   The raw response also has a sideboard. It is intentionally excluded.
 *
 * @param {object} rawDeck
 * @returns {Array<object>}
 */
function extractDeckRecords(rawDeck) {
  if (rawDeck === null || typeof rawDeck !== "object") {
    throw new TypeError(`Unable to interpret raw deck data: ${typeof rawDeck}`);
  }

  const boards = rawDeck.boards;
  if (boards === null || typeof boards !== "object") {
    throw new TypeError("Raw Moxfield deck is missing the expected 'boards' object.");
  }

  const commander = extractRawBoardCards(boards.commanders);
  const mainboard = extractRawBoardCards(boards.mainboard);

  const records = [...commander, ...mainboard];

  if (records.length === 0) {
    throw new TypeError(
      "Raw Moxfield deck contained boards, but no commander/mainboard cards could be extracted."
    );
  }

  return records;
}

module.exports = {
  normalizedDeckRecords,
  buildRequirements,
  extractRawBoardCards,
  extractDeckRecords,
};
