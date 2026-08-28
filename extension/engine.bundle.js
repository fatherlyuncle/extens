var MoxfieldEngine = (() => {
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __commonJS = (cb, mod) => function __require() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };

  // src/engine_js/collection.js
  var require_collection = __commonJS({
    "src/engine_js/collection.js"(exports, module) {
      function buildCollectionIndex(collection) {
        if (!Array.isArray(collection)) {
          throw new TypeError("Normalized collection must be an array.");
        }
        const index = /* @__PURE__ */ new Map();
        for (const record of collection) {
          if (record === null || typeof record !== "object") continue;
          const name = record.name;
          if (name) index.set(String(name), record);
        }
        return index;
      }
      module.exports = { buildCollectionIndex };
    }
  });

  // src/engine_js/util.js
  var require_util = __commonJS({
    "src/engine_js/util.js"(exports, module) {
      function qty(record) {
        const raw = record && Object.prototype.hasOwnProperty.call(record, "quantity") ? record.quantity : 1;
        const n = Number(raw);
        if (!Number.isFinite(n)) return 1;
        return Math.max(Math.trunc(n), 0);
      }
      function toCents(value) {
        if (value === null || value === void 0 || value === "") return null;
        const n = Number(value);
        if (!Number.isFinite(n) || n < 0) return null;
        return Math.round(n * 100);
      }
      function formatCents(cents) {
        const sign = cents < 0 ? "-" : "";
        const abs = Math.abs(cents);
        const dollars = Math.floor(abs / 100);
        const rem = abs % 100;
        return `${sign}$${dollars}.${String(rem).padStart(2, "0")}`;
      }
      module.exports = { qty, toCents, formatCents };
    }
  });

  // src/engine_js/deck.js
  var require_deck = __commonJS({
    "src/engine_js/deck.js"(exports, module) {
      var { qty } = require_util();
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
              scryfallId: record.scryfall_id ?? null
            });
          }
        }
        return requirements;
      }
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
        extractDeckRecords
      };
    }
  });

  // src/engine_js/matching.js
  var require_matching = __commonJS({
    "src/engine_js/matching.js"(exports, module) {
      function matchDeck(requirements, collectionIndex) {
        const results = [];
        for (const req of requirements) {
          const required = req.quantity;
          const collection = collectionIndex.get(req.name);
          let ownedTotal = 0;
          if (collection) {
            const n = Number(collection.total_quantity);
            ownedTotal = Number.isFinite(n) ? n : 0;
          }
          const owned = Math.min(Math.max(ownedTotal, 0), required);
          const missing = required - owned;
          results.push({
            name: req.name,
            quantity: req.quantity,
            finish: req.finish,
            scryfallId: req.scryfallId,
            board: req.board,
            required,
            owned,
            missing,
            collectionRecord: collection ?? null
          });
        }
        return results;
      }
      module.exports = { matchDeck };
    }
  });

  // src/engine_js/pricing.js
  var require_pricing = __commonJS({
    "src/engine_js/pricing.js"(exports, module) {
      var { toCents } = require_util();
      function buildRawPriceCatalog(rawRecords) {
        const catalog = /* @__PURE__ */ new Map();
        for (const record of rawRecords) {
          const name = record.name;
          if (!name) continue;
          const key = String(name);
          if (!catalog.has(key)) catalog.set(key, []);
          catalog.get(key).push(record);
        }
        return catalog;
      }
      var FINISH_FIELDS = [
        ["nonFoil", "usd"],
        ["foil", "usd_foil"],
        ["etched", "usd_etched"]
      ];
      function priceOptions(record) {
        const prices = record.prices;
        if (prices === null || typeof prices !== "object") return [];
        const result = [];
        for (const [finish, field] of FINISH_FIELDS) {
          const cents = toCents(prices[field]);
          if (cents !== null) {
            result.push({ finish, priceField: field, priceCents: cents });
          }
        }
        return result;
      }
      function selectPrice(records, strategy) {
        const candidates = [];
        for (const record of records) {
          let options = priceOptions(record);
          const requestedFinish = record.finish || "nonFoil";
          if (strategy === "same") {
            options = options.filter((x) => x.finish === requestedFinish);
          }
          for (const option of options) {
            candidates.push({ ...option, record });
          }
        }
        if (candidates.length === 0) return null;
        if (strategy === "same") {
          return candidates[0];
        }
        if (strategy === "cheapest") {
          return candidates.reduce((min, c) => c.priceCents < min.priceCents ? c : min);
        }
        if (strategy === "most_expensive") {
          return candidates.reduce((max, c) => c.priceCents > max.priceCents ? c : max);
        }
        throw new Error(`Unknown price strategy: ${strategy}`);
      }
      module.exports = { buildRawPriceCatalog, priceOptions, selectPrice };
    }
  });

  // src/engine_js/engine.js
  var require_engine = __commonJS({
    "src/engine_js/engine.js"(exports, module) {
      var { buildCollectionIndex } = require_collection();
      var { buildRequirements, extractDeckRecords } = require_deck();
      var { matchDeck } = require_matching();
      var { buildRawPriceCatalog, selectPrice } = require_pricing();
      function calculateDeckCost({
        collection,
        normalizedDeck,
        rawDeck,
        pricingStrategy = "cheapest",
        includeCommander = true
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
            lineTotalCents
          });
        }
        return {
          required,
          owned,
          missing,
          pricedQuantity,
          unpricedQuantity,
          costCents,
          selections
        };
      }
      module.exports = { calculateDeckCost };
    }
  });

  // src/engine_js/index.js
  var require_index = __commonJS({
    "src/engine_js/index.js"(exports, module) {
      var { calculateDeckCost } = require_engine();
      var { formatCents } = require_util();
      module.exports = { calculateDeckCost, formatCents };
    }
  });

  // src/adapters_js/moxfieldDeck.js
  var require_moxfieldDeck = __commonJS({
    "src/adapters_js/moxfieldDeck.js"(exports, module) {
      function getBoardCards(deck, boardName) {
        const boards = deck.boards;
        if (boards === null || typeof boards !== "object") {
          throw new Error("Deck response does not contain a valid 'boards' object.");
        }
        const board = boards[boardName];
        if (board === null || typeof board !== "object") return {};
        const cards = board.cards;
        if (cards === null || cards === void 0) return {};
        if (typeof cards !== "object") {
          throw new Error(`Board '${boardName}' does not contain a valid 'cards' object.`);
        }
        return cards;
      }
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
        if (quantity === null || quantity === void 0) quantity = 1;
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
      function normalizeDeck(deck) {
        const commanderCards = getBoardCards(deck, "commanders");
        const mainboardCards = getBoardCards(deck, "mainboard");
        return {
          name: deck.name,
          format: deck.format,
          commander: normalizeBoard(commanderCards),
          mainboard: normalizeBoard(mainboardCards)
        };
      }
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
    }
  });

  // src/engine_js/browser-entry.js
  var require_browser_entry = __commonJS({
    "src/engine_js/browser-entry.js"(exports, module) {
      var engine = require_index();
      var deckAdapter = require_moxfieldDeck();
      module.exports = {
        ...engine,
        ...deckAdapter
      };
    }
  });
  return require_browser_entry();
})();
