/**
 * util.js
 * -------
 * Small shared helpers used across the engine modules.
 *
 * Money is represented internally as integer CENTS, not floating-point
 * dollars. This mirrors the role Python's Decimal played in deck_cost.py
 * (avoiding floating-point drift on currency), without needing an
 * external decimal library -- which matters for a Manifest V3 extension,
 * since MV3 disallows loading remote code and we'd otherwise have to
 * bundle a dependency just for this.
 *
 * All prices in the fixture/Scryfall data are 2-decimal USD values, so
 * `Math.round(dollars * 100)` is a safe, exact conversion to cents.
 */

/**
 * Parse a quantity field the same way deck_cost.py's qty() does:
 * default to 1, clamp negatives to 0, tolerate garbage input.
 * @param {object} record
 * @returns {number}
 */
function qty(record) {
  const raw = record && Object.prototype.hasOwnProperty.call(record, "quantity")
    ? record.quantity
    : 1;
  const n = Number(raw);
  if (!Number.isFinite(n)) return 1;
  return Math.max(Math.trunc(n), 0);
}

/**
 * Convert a dollar value (number, numeric string, null, or "") to integer
 * cents, or null if it isn't a valid non-negative price. Mirrors
 * deck_cost.py's dec() but returns cents instead of Decimal dollars.
 * @param {*} value
 * @returns {number|null}
 */
function toCents(value) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return null;
  return Math.round(n * 100);
}

/**
 * Format integer cents as a "$X.XX" string.
 * @param {number} cents
 * @returns {string}
 */
function formatCents(cents) {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const rem = abs % 100;
  return `${sign}$${dollars}.${String(rem).padStart(2, "0")}`;
}

module.exports = { qty, toCents, formatCents };
