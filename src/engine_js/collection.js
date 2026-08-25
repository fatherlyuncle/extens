/**
 * collection.js
 * -------------
 * Port of src/engine/collection.py -- no behavior change.
 */

/**
 * Build a name -> collection-record index from the normalized collection
 * (an array of {name, total_quantity, unique_printings} objects).
 * @param {Array<object>} collection
 * @returns {Map<string, object>}
 */
function buildCollectionIndex(collection) {
  if (!Array.isArray(collection)) {
    throw new TypeError("Normalized collection must be an array.");
  }

  const index = new Map();
  for (const record of collection) {
    if (record === null || typeof record !== "object") continue;
    const name = record.name;
    if (name) index.set(String(name), record);
  }
  return index;
}

module.exports = { buildCollectionIndex };
