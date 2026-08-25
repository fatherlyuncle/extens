/**
 * models.js
 * ---------
 * Public/domain object shapes for the deck-cost engine.
 *
 * JS has no built-in dataclass equivalent, and adding a class hierarchy
 * for plain data records would be more machinery than this needs. These
 * are documented as JSDoc typedefs instead -- they describe the exact
 * same fields as the Python dataclasses in src/engine/models.py, and
 * exist so editors/type-checkers can validate shapes without adding a
 * runtime dependency.
 *
 * Money fields are integer CENTS here (unitPriceCents, lineTotalCents,
 * costCents), not dollars -- see util.js for why.
 */

/**
 * @typedef {Object} CardRequirement
 * @property {string} name
 * @property {number} quantity
 * @property {"commander"|"mainboard"} board
 * @property {string} finish
 * @property {string|null} scryfallId
 */

/**
 * @typedef {Object} MatchResult
 * @property {number} required
 * @property {number} owned
 * @property {number} missing
 */

/**
 * @typedef {Object} PriceSelection
 * @property {string} cardName
 * @property {string} setCode
 * @property {string} collectorNumber
 * @property {string} finish
 * @property {string} priceField
 * @property {number} unitPriceCents
 * @property {number} quantity
 * @property {number} lineTotalCents
 */

/**
 * @typedef {Object} DeckCostResult
 * @property {number} required
 * @property {number} owned
 * @property {number} missing
 * @property {number} pricedQuantity
 * @property {number} unpricedQuantity
 * @property {number} costCents
 * @property {PriceSelection[]} selections
 */

module.exports = {};
