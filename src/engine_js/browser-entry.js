/**
 * browser-entry.js
 * -----------------
 * Single entry point for bundling the engine + deck adapter into one
 * browser-compatible file via esbuild. This is NOT itself part of the
 * public API surface -- it exists purely so the extension's content
 * script has one script tag to load, exposing everything it needs as
 * a single global (see extension/build.js for the esbuild invocation
 * and global name).
 *
 * The collection adapter (moxfieldCollection.js) is intentionally NOT
 * included here: the extension currently ships a pre-normalized
 * collection snapshot (built at bundle time from the existing
 * collection_normalized.json), so no raw-collection normalization
 * needs to happen in the browser yet. That adapter will be added here
 * once live, authenticated collection fetching is implemented.
 */

const engine = require("./index");
const deckAdapter = require("../adapters_js/moxfieldDeck");

module.exports = {
  ...engine,
  ...deckAdapter,
};
