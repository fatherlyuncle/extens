/**
 * moxfieldDeck.js
 * ----------------
 * Port of test/normdeck.py's normalize_deck() -- no behavior change.
 *
 * This is the deck-side counterpart to moxfieldCollection.js. The
 * engine's calculateDeckCost() takes both a `normalizedDeck` (simple
 * {commander, mainboard} lists of {name, quantity, finish,
 * scryfallId}) and a `rawDeck` (the full raw Moxfield API response,
 * used internally for printing/price lookups). This module produces
 * the former from the latter.
 *
 * Sideboard, considering/maybeboard, companions, and all other boards
 * are intentionally excluded -- matching normdeck.py exactly.
 */

/**
 * Return the card map for a specific Moxfield board.
 *
 * Moxfield's current v3 deck response stores cards under:
 *
 *   boards
 *     └── <boardName>
 *           └── cards
 *
 * An empty object is returned if the board does not exist.
 *
 * @param {object} deck
 * @param {string} boardName
 * @returns {object}
 */
function getBoardCards(deck, boardName) {
  const boards = deck.boards;
  if (boards === null || typeof boards !== "object") {
    throw new Error("Deck response does not contain a valid 'boards' object.");
  }

  const board = boards[boardName];
  if (board === null || typeof board !== "object") return {};

  const cards = board.cards;
  if (cards === null || cards === undefined) return {};
  if (typeof cards !== "object") {
    throw new Error(`Board '${boardName}' does not contain a valid 'cards' object.`);
  }

  return cards;
}

/**
 * Convert one raw Moxfield deck card entry into the simplified
 * representation used by the normalized deck shape.
 *
 * @param {string} cardId
 * @param {object} entry
 * @returns {{name: string, quantity: number, finish: string|null, scryfallId: string|null}}
 */
function normalizeCard(cardId, entry) {
  if (entry === null || typeof entry !== "object") {
    throw new Error(`Invalid card entry for '${cardId}'.`);
  }

  const card = entry.card;
  if (card === null || typeof card !== "object") {
    throw new Error(`Card entry '${cardId}' does not contain a valid card object.`);
  }

  const name = card.name;
  if (!name) {
    throw new Error(`Card entry '${cardId}' does not contain a card name.`);
  }

  let quantity = entry.quantity;
  if (quantity === null || quantity === undefined) quantity = 1;
  if (!Number.isInteger(quantity)) {
    throw new Error(`Invalid quantity for '${name}': ${JSON.stringify(quantity)}`);
  }
  if (quantity < 1) {
    throw new Error(`Invalid quantity for '${name}': ${quantity}`);
  }

  const finish = entry.finish ?? null;
  const scryfallId = card.scryfall_id ?? null;

  return { name, quantity, finish, scryfallId };
}

/**
 * Normalize all cards in a Moxfield board.
 *
 * The output remains an array because the deck represents individual
 * deck entries rather than an ownership aggregate.
 *
 * @param {object} cards
 * @returns {Array<{name: string, quantity: number, finish: string|null, scryfallId: string|null}>}
 */
function normalizeBoard(cards) {
  const normalized = [];
  for (const [cardId, entry] of Object.entries(cards)) {
    normalized.push(normalizeCard(cardId, entry));
  }

  normalized.sort((a, b) => {
    const keyA = [a.name.toLowerCase(), String(a.scryfallId || "").toLowerCase(), String(a.finish || "").toLowerCase()];
    const keyB = [b.name.toLowerCase(), String(b.scryfallId || "").toLowerCase(), String(b.finish || "").toLowerCase()];
    for (let i = 0; i < keyA.length; i++) {
      if (keyA[i] < keyB[i]) return -1;
      if (keyA[i] > keyB[i]) return 1;
    }
    return 0;
  });

  return normalized;
}

/**
 * Normalize the Commander and Mainboard portions of a Moxfield deck.
 *
 * Sideboard, considering/maybeboard, companions, and all other boards
 * are intentionally excluded.
 *
 * @param {object} deck - raw Moxfield deck API response.
 * @returns {{name: string|undefined, format: string|undefined, commander: Array, mainboard: Array}}
 */
function normalizeDeck(deck) {
  const commanderCards = getBoardCards(deck, "commanders");
  const mainboardCards = getBoardCards(deck, "mainboard");

  return {
    name: deck.name,
    format: deck.format,
    commander: normalizeBoard(commanderCards),
    mainboard: normalizeBoard(mainboardCards),
  };
}

/**
 * Verify that normalization preserved the Commander and Mainboard
 * card quantities. Sideboard and other boards are intentionally
 * ignored. Throws on any mismatch.
 *
 * @param {object} rawDeck
 * @param {object} normalizedDeck
 */
function validateNormalizedDeck(rawDeck, normalizedDeck) {
  const rawCommanders = getBoardCards(rawDeck, "commanders");
  const rawMainboard = getBoardCards(rawDeck, "mainboard");

  const rawCommanderQty = Object.values(rawCommanders).reduce((sum, e) => sum + (e.quantity ?? 1), 0);
  const rawMainboardQty = Object.values(rawMainboard).reduce((sum, e) => sum + (e.quantity ?? 1), 0);

  const normCommanderQty = normalizedDeck.commander.reduce((sum, c) => sum + c.quantity, 0);
  const normMainboardQty = normalizedDeck.mainboard.reduce((sum, c) => sum + c.quantity, 0);

  if (rawCommanderQty !== normCommanderQty) {
    throw new Error(
      `Commander quantity was not preserved (raw: ${rawCommanderQty}, normalized: ${normCommanderQty}).`
    );
  }
  if (rawMainboardQty !== normMainboardQty) {
    throw new Error(
      `Mainboard quantity was not preserved (raw: ${rawMainboardQty}, normalized: ${normMainboardQty}).`
    );
  }
}

module.exports = { getBoardCards, normalizeCard, normalizeBoard, normalizeDeck, validateNormalizedDeck };
