/**
 * pricing.js
 * ----------
 * Port of src/engine/pricing.py -- no behavior change, except prices
 * are integer CENTS (via toCents) instead of Python Decimal dollars.
 * See util.js for why.
 */

const { toCents } = require("./util");

/**
 * @param {Array<object>} rawRecords
 * @returns {Map<string, object[]>}
 */
function buildRawPriceCatalog(rawRecords) {
  const catalog = new Map();

  for (const record of rawRecords) {
    const name = record.name;
    if (!name) continue;
    const key = String(name);
    if (!catalog.has(key)) catalog.set(key, []);
    catalog.get(key).push(record);
  }

  return catalog;
}

const FINISH_FIELDS = [
  ["nonFoil", "usd"],
  ["foil", "usd_foil"],
  ["etched", "usd_etched"],
];

/**
 * @param {object} record
 * @returns {Array<{finish: string, priceField: string, priceCents: number}>}
 */
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

/**
 * @param {Array<object>} records
 * @param {"same"|"cheapest"|"most_expensive"} strategy
 * @returns {{finish: string, priceField: string, priceCents: number, record: object}|null}
 */
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
    return candidates.reduce((min, c) => (c.priceCents < min.priceCents ? c : min));
  }
  if (strategy === "most_expensive") {
    return candidates.reduce((max, c) => (c.priceCents > max.priceCents ? c : max));
  }

  throw new Error(`Unknown price strategy: ${strategy}`);
}

module.exports = { buildRawPriceCatalog, priceOptions, selectPrice };
