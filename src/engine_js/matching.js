/**
 * matching.js
 * -----------
 * Port of src/engine/matching.py -- no behavior change.
 */

/**
 * @param {import('./models').CardRequirement[]} requirements
 * @param {Map<string, object>} collectionIndex
 * @returns {Array<object>} per-card match records (plain objects, same
 *   shape as the Python dict version -- not elevated to a public type,
 *   see models.js docstring for why)
 */
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
      collectionRecord: collection ?? null,
    });
  }

  return results;
}

module.exports = { matchDeck };
