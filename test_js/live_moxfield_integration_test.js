#!/usr/bin/env node
/**
 * live_moxfield_integration_test.js
 * ===================================
 *
 * NOTE ON DETERMINISM: this test fetches a REAL, LIVE deck from
 * Moxfield's API. Its owner could edit it, card prices fluctuate, and
 * Moxfield's response shape could change without notice (Moxfield has
 * no official public API -- everything here is reverse-engineered).
 * This test therefore does NOT assert exact dollar totals the way
 * test_js/integration_test.js and test_js/adapter_integration_test.js
 * do against their frozen fixtures. It asserts structural correctness
 * and internal consistency instead. If it starts failing, that's a
 * signal to go look at what changed on Moxfield's end -- not a sign
 * the assertions themselves are wrong.
 *
 * SCOPE: this test intentionally does NOT attempt a live collection
 * fetch. Moxfield's collection endpoint requires an authenticated
 * session (Bearer token obtained via a cookie-based login flow), which
 * a standalone Node script has no legitimate way to obtain -- it isn't
 * running inside a logged-in browser tab. Rather than scrape or reuse
 * old credentials (which wouldn't validate the actual mechanism the
 * real extension will use -- a content script inheriting the
 * browser's live session cookies automatically), this test uses the
 * EXISTING collection data already captured in this repo
 * (test/moxfield/collection.json if present, else
 * collection_normalized.json) and live-fetches only the deck side.
 * Live, authenticated collection access is deferred until the actual
 * browser-extension content-script phase.
 *
 * What this proves:
 *
 *   LIVE Moxfield deck API response
 *       -> existing JS deck adapter (moxfieldDeck.normalizeDeck)
 *       -> existing collection data (local capture + adapter, or
 *          pre-normalized fixture)
 *       -> calculateDeckCost() [existing public engine API]
 *       -> structurally valid, internally consistent result
 *
 * No DOM code, no browser automation, no UI rendering here -- this is
 * still a backend/data integration test.
 *
 * Run with:
 *
 *   node test_js/live_moxfield_integration_test.js
 */

const fs = require("fs");
const path = require("path");

const { normalizeDeck, validateNormalizedDeck } = require("../src/adapters_js/moxfieldDeck");
const {
  normalizeCollection,
  toEngineCollectionFormat,
  validateNormalizedCollection,
} = require("../src/adapters_js/moxfieldCollection");
const { calculateDeckCost, formatCents } = require("../src/engine_js");

const MOXFIELD_DIR = path.join(__dirname, "..", "test", "moxfield");
const FULL_COLLECTION_PATH = path.join(MOXFIELD_DIR, "collection.json");
const NORMALIZED_COLLECTION_PATH = path.join(MOXFIELD_DIR, "collection_normalized.json");

// Same public deck used by every other fixture test in this project.
// Confirmed to match test/moxfield/testdeck.json's own publicId field.
const DECK_ID = "v35AP7qQd0-Lj7XVg7UmBA";

// Established, working endpoint/headers -- taken directly from
// test/compile_deck.py, which already proved this contract works.
// Not guessing a new one.
const MOXFIELD_VERSION = "2026.08.13.2";
const DECK_URL = `https://api2.moxfield.com/v3/decks/all/${DECK_ID}`;
const REQUEST_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0",
  Accept: "application/json, text/plain, */*",
  "Accept-Language": "en-US,en;q=0.9",
  "x-moxfield-version": MOXFIELD_VERSION,
  Origin: "https://moxfield.com",
  Referer: "https://moxfield.com/",
};

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

class LiveApiRequestError extends Error {}
class AdapterValidationError extends Error {}
class EngineValidationError extends Error {}

// ---------------------------------------------------------------------
// Step: fetch the live deck
// ---------------------------------------------------------------------

async function fetchLiveDeck() {
  console.log("Requesting live Moxfield deck...");
  console.log(`  URL: ${DECK_URL}`);

  let response;
  try {
    response = await fetch(DECK_URL, { headers: REQUEST_HEADERS });
  } catch (err) {
    throw new LiveApiRequestError(
      `Network error requesting ${DECK_URL}: ${err.message}`
    );
  }

  console.log(`  HTTP status: ${response.status} ${response.statusText}`);

  if (!response.ok) {
    let bodyPreview = "";
    try {
      bodyPreview = (await response.text()).slice(0, 500);
    } catch {
      // ignore
    }
    throw new LiveApiRequestError(
      `Moxfield deck request failed.\n` +
        `  URL: ${DECK_URL}\n` +
        `  HTTP status: ${response.status} ${response.statusText}\n` +
        (bodyPreview ? `  Body preview: ${bodyPreview}` : "")
    );
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    throw new LiveApiRequestError(
      `Moxfield returned a response that was not valid JSON: ${err.message}`
    );
  }

  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    throw new LiveApiRequestError("Expected the Moxfield deck response to be a JSON object.");
  }

  if (!data.boards || typeof data.boards !== "object") {
    throw new LiveApiRequestError(
      "Live deck response does not contain the expected 'boards' object. " +
        "Moxfield's response shape may have changed."
    );
  }

  return data;
}

// ---------------------------------------------------------------------
// Step: load the existing local collection (NOT a live fetch)
// ---------------------------------------------------------------------

function loadExistingCollection() {
  if (fs.existsSync(FULL_COLLECTION_PATH)) {
    console.log(`  Using full raw capture: ${FULL_COLLECTION_PATH}`);
    const rawCollection = loadJson(FULL_COLLECTION_PATH);
    const normalized = normalizeCollection(rawCollection);
    validateNormalizedCollection(rawCollection, normalized);
    return {
      collection: toEngineCollectionFormat(normalized),
      rawRecordCount: rawCollection.length,
      normalizedNameCount: normalized.length,
    };
  }

  if (fs.existsSync(NORMALIZED_COLLECTION_PATH)) {
    console.log(`  Full raw capture not found; using pre-normalized fixture: ${NORMALIZED_COLLECTION_PATH}`);
    const collection = loadJson(NORMALIZED_COLLECTION_PATH);
    return {
      collection,
      rawRecordCount: null,
      normalizedNameCount: collection.length,
    };
  }

  throw new AdapterValidationError(
    "No local collection data found. Expected one of:\n" +
      `  ${FULL_COLLECTION_PATH}\n` +
      `  ${NORMALIZED_COLLECTION_PATH}`
  );
}

// ---------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------

async function main() {
  console.log("=".repeat(60));
  console.log("LIVE MOXFIELD API INTEGRATION TEST");
  console.log("=".repeat(60));
  console.log();

  // -- 1. Live deck fetch --------------------------------------------
  let rawDeck;
  try {
    rawDeck = await fetchLiveDeck();
  } catch (err) {
    console.log();
    console.log("-".repeat(60));
    console.log("LIVE API REQUEST FAILED");
    console.log("-".repeat(60));
    console.log(err.message);
    process.exit(1);
  }

  console.log();
  console.log(`Deck name:   ${rawDeck.name}`);
  console.log(`Deck format: ${rawDeck.format}`);
  console.log(`Deck ID:     ${rawDeck.id ?? "(not present)"}`);
  console.log();

  // -- 2. Adapter validation -------------------------------------------
  let normalizedDeck;
  let existingCollectionInfo;
  try {
    console.log("Normalizing live deck via existing deck adapter...");
    normalizedDeck = normalizeDeck(rawDeck);
    validateNormalizedDeck(rawDeck, normalizedDeck);
    console.log("  Deck quantity preservation: PASS");

    console.log();
    console.log("Loading existing local collection data (not live-fetched)...");
    existingCollectionInfo = loadExistingCollection();
    console.log(`  Normalized collection card names: ${existingCollectionInfo.normalizedNameCount}`);
  } catch (err) {
    console.log();
    console.log("-".repeat(60));
    console.log("ADAPTER VALIDATION FAILED");
    console.log("-".repeat(60));
    console.log(err.message);
    process.exit(1);
  }

  // -- 3. Engine + structural/consistency validation --------------------
  let results;
  try {
    console.log();
    console.log("Running calculateDeckCost() for all three pricing strategies...");
    results = {};
    for (const strategy of ["same", "cheapest", "most_expensive"]) {
      const result = calculateDeckCost({
        collection: existingCollectionInfo.collection,
        normalizedDeck,
        rawDeck,
        pricingStrategy: strategy,
      });
      results[strategy] = result;
    }

    const any = results.cheapest;

    // Structural checks.
    for (const strategy of ["same", "cheapest", "most_expensive"]) {
      const r = results[strategy];
      assert(typeof r.required === "number", `${strategy}: required is not a number`);
      assert(typeof r.owned === "number", `${strategy}: owned is not a number`);
      assert(typeof r.missing === "number", `${strategy}: missing is not a number`);
      assert(Number.isFinite(r.costCents), `${strategy}: costCents is not finite`);
      assert(r.costCents >= 0, `${strategy}: costCents is negative`);
      assert(
        r.required === r.owned + r.missing,
        `${strategy}: required (${r.required}) !== owned (${r.owned}) + missing (${r.missing})`
      );
      assert(
        r.pricedQuantity + r.unpricedQuantity === r.missing,
        `${strategy}: pricedQuantity + unpricedQuantity !== missing`
      );
    }

    // required/owned/missing must agree across strategies (pricing
    // strategy doesn't affect matching).
    const requiredSet = new Set(Object.values(results).map((r) => r.required));
    const ownedSet = new Set(Object.values(results).map((r) => r.owned));
    const missingSet = new Set(Object.values(results).map((r) => r.missing));
    assert(requiredSet.size === 1, "required differs across pricing strategies");
    assert(ownedSet.size === 1, "owned differs across pricing strategies");
    assert(missingSet.size === 1, "missing differs across pricing strategies");

    // Pricing invariant guaranteed by the engine's actual semantics:
    // cheapest <= same <= most_expensive (see pricing.js's selectPrice:
    // "same" is constrained to one finish, "cheapest"/"most_expensive"
    // search across all available finishes, so cheapest can only tie
    // or beat "same", and "same" can only tie or beat most_expensive
    // is NOT guaranteed in general -- but most_expensive searches the
    // same candidate pool as cheapest and takes the max, so
    // same <= most_expensive holds whenever "same"'s single-finish
    // price is within that pool, which it always is by construction).
    assert(
      results.cheapest.costCents <= results.same.costCents,
      `cheapest (${formatCents(results.cheapest.costCents)}) > same (${formatCents(results.same.costCents)})`
    );
    assert(
      results.same.costCents <= results.most_expensive.costCents,
      `same (${formatCents(results.same.costCents)}) > most_expensive (${formatCents(results.most_expensive.costCents)})`
    );

    console.log("  All structural and consistency checks: PASS");
  } catch (err) {
    console.log();
    console.log("-".repeat(60));
    console.log("ENGINE VALIDATION FAILED");
    console.log("-".repeat(60));
    console.log(err.message);
    process.exit(1);
  }

  // -- 4. Report ---------------------------------------------------------
  const any = results.cheapest;
  console.log();
  console.log("-".repeat(60));
  console.log("LIVE TEST RESULTS (informational -- not asserted against fixed values)");
  console.log("-".repeat(60));
  console.log(`Deck name:                    ${rawDeck.name}`);
  console.log(`Deck ID:                      ${DECK_ID}`);
  if (existingCollectionInfo.rawRecordCount !== null) {
    console.log(`Local raw collection records: ${existingCollectionInfo.rawRecordCount}`);
  }
  console.log(`Local normalized card names:  ${existingCollectionInfo.normalizedNameCount}`);
  console.log();
  console.log(`Required: ${any.required}`);
  console.log(`Owned:    ${any.owned}`);
  console.log(`Missing:  ${any.missing}`);
  console.log();
  console.log(`Same:            ${formatCents(results.same.costCents)}`);
  console.log(`Cheapest:        ${formatCents(results.cheapest.costCents)}`);
  console.log(`Most expensive:  ${formatCents(results.most_expensive.costCents)}`);
  console.log();
  console.log("Reference fixture numbers (test_js/integration_test.js), for comparison only:");
  console.log("  Required: 100, Owned: 68, Missing: 32");
  console.log("  Same: $48.68, Cheapest: $48.41, Most expensive: $87.48");
  console.log();
  console.log("=".repeat(60));
  console.log("LIVE MOXFIELD API INTEGRATION TEST PASSED");
  console.log("=".repeat(60));
  process.exit(0);
}

main();
