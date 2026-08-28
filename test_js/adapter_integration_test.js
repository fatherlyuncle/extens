#!/usr/bin/env node
/**
 * adapter_integration_test.js
 * =============================
 *
 * Validates src/adapters_js/moxfieldCollection.js against the REAL,
 * COMPLETE raw collection capture (14,953 records, not the 50-record
 * sample page), and proves the full real-data path end-to-end:
 *
 *   raw collection.json (real Moxfield API capture)
 *       -> normalizeCollection() / toEngineCollectionFormat()
 *       -> calculateDeckCost()
 *       -> same reference numbers as the pre-normalized fixture
 *
 * This is a stronger check than test_js/integration_test.js, which
 * uses the pre-normalized collection_normalized.json fixture. This
 * test instead exercises the adapter that will actually sit between
 * a real Moxfield API response and the engine in the shipped
 * extension.
 *
 * Requires test/moxfield/collection.json -- the complete raw
 * collection capture. If it isn't present, this test is skipped
 * with a clear message rather than failing (it's a large file that
 * may not always be checked into every environment).
 *
 * Run with:
 *
 *   node test_js/adapter_integration_test.js
 */

const fs = require("fs");
const path = require("path");

const {
  normalizeCollection,
  toEngineCollectionFormat,
  validateNormalizedCollection,
} = require("../src/adapters_js/moxfieldCollection");
const { calculateDeckCost, formatCents } = require("../src/engine_js");

const MOXFIELD_DIR = path.join(__dirname, "..", "test", "moxfield");
const FULL_COLLECTION_PATH = path.join(MOXFIELD_DIR, "collection.json");
const EXISTING_NORMALIZED_PATH = path.join(MOXFIELD_DIR, "collection_normalized.json");
const NORMALIZED_DECK_PATH = path.join(MOXFIELD_DIR, "testdeck_normalized.json");
const RAW_DECK_PATH = path.join(MOXFIELD_DIR, "testdeck.json");

const EXPECTED_TOTALS_CENTS = { same: 4868, cheapest: 4841, most_expensive: 8748 };

function loadJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function main() {
  if (!fs.existsSync(FULL_COLLECTION_PATH)) {
    console.log(
      `SKIPPED: ${FULL_COLLECTION_PATH} not found. This test requires the ` +
        "full 14,953-record raw collection capture, which is large and may " +
        "not be present in every environment."
    );
    process.exit(0);
  }

  console.log("=".repeat(60));
  console.log("COLLECTION ADAPTER INTEGRATION TEST (real full capture)");
  console.log("=".repeat(60));
  console.log();

  console.log("[1/4] Loading full raw collection capture...");
  const rawCollection = loadJson(FULL_COLLECTION_PATH);
  assert(Array.isArray(rawCollection), "raw collection must be an array");
  console.log(`      ${rawCollection.length} raw records loaded.`);

  console.log("[2/4] Normalizing + validating quantity preservation...");
  const normalized = normalizeCollection(rawCollection);
  validateNormalizedCollection(rawCollection, normalized);
  console.log(`      ${normalized.length} unique card names, validation PASS.`);

  console.log("[3/4] Cross-checking against existing Python-normalized output...");
  const existing = loadJson(EXISTING_NORMALIZED_PATH);
  const engineFormat = toEngineCollectionFormat(normalized);
  const existingByName = new Map(existing.map((c) => [c.name, c]));

  assert(
    engineFormat.length === existing.length,
    `expected ${existing.length} names, got ${engineFormat.length}`
  );

  let mismatches = 0;
  for (const card of engineFormat) {
    const ref = existingByName.get(card.name);
    if (!ref || ref.total_quantity !== card.total_quantity) mismatches++;
  }
  assert(mismatches === 0, `${mismatches} card(s) disagree with the Python-normalized reference`);
  console.log(`      All ${engineFormat.length} names match Python output exactly.`);

  console.log("[4/4] Running calculateDeckCost() end-to-end with real collection data...");
  const normalizedDeck = loadJson(NORMALIZED_DECK_PATH);
  const rawDeck = loadJson(RAW_DECK_PATH);

  const results = {};
  for (const strategy of ["same", "cheapest", "most_expensive"]) {
    results[strategy] = calculateDeckCost({
      collection: engineFormat,
      normalizedDeck,
      rawDeck,
      pricingStrategy: strategy,
    });
  }

  const any = results.cheapest;
  assert(any.required === 100, `expected required 100, got ${any.required}`);
  assert(any.owned === 68, `expected owned 68, got ${any.owned}`);
  assert(any.missing === 32, `expected missing 32, got ${any.missing}`);

  for (const [strategy, expectedCents] of Object.entries(EXPECTED_TOTALS_CENTS)) {
    assert(
      results[strategy].costCents === expectedCents,
      `${strategy}: expected ${formatCents(expectedCents)}, got ${formatCents(results[strategy].costCents)}`
    );
  }
  console.log("      Reference numbers reproduced exactly using real collection data.");

  console.log();
  console.log("-".repeat(60));
  console.log("Required:", any.required, " Owned:", any.owned, " Missing:", any.missing);
  console.log("Same:", formatCents(results.same.costCents));
  console.log("Cheapest:", formatCents(results.cheapest.costCents));
  console.log("Most expensive:", formatCents(results.most_expensive.costCents));
  console.log("-".repeat(60));
  console.log();
  console.log("ADAPTER INTEGRATION TEST PASSED");
  process.exit(0);
}

try {
  main();
} catch (err) {
  console.error("FAILED:", err.message);
  process.exit(1);
}
