#!/usr/bin/env node
/**
 * integration_test.js
 * ====================
 *
 * End-to-end integration test for the JS port of the deck-cost engine
 * (src/engine_js/). Mirrors test/integration_test.py exactly: same
 * fixtures, same expected numbers, same stage structure. This is the
 * gate for the JS port -- it must match the Python reference before any
 * extension/DOM work begins.
 *
 * No browser, no DOM, no extension APIs are used here. This runs under
 * plain Node so it can be checked in CI or from the command line the
 * same way as the Python test.
 *
 * Expected reference numbers (from deck_cost.py / test/integration_test.py):
 *
 *   Required: 100
 *   Owned:    68
 *   Missing:  32
 *
 *   same             $48.68
 *   cheapest         $48.41
 *   most_expensive   $87.48
 *
 *   priced_quantity=32, unpriced_quantity=0 for every strategy
 *
 * Run with:
 *
 *   node test_js/integration_test.js
 */

const fs = require("fs");
const path = require("path");

const { calculateDeckCost, formatCents } = require("../src/engine_js");
const { selectPrice } = require("../src/engine_js/pricing");
const { buildRawPriceCatalog } = require("../src/engine_js/pricing");
const { extractDeckRecords } = require("../src/engine_js/deck");

const MOXFIELD_DIR = path.join(__dirname, "..", "test", "moxfield");
const COLLECTION_PATH = path.join(MOXFIELD_DIR, "collection_normalized.json");
const NORMALIZED_DECK_PATH = path.join(MOXFIELD_DIR, "testdeck_normalized.json");
const RAW_DECK_PATH = path.join(MOXFIELD_DIR, "testdeck.json");

const TOTAL_STAGES = 5;

const EXPECTED_TOTALS_CENTS = {
  same: 4868,
  cheapest: 4841,
  most_expensive: 8748,
};

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function report(stageNum, label, status) {
  const dots = ".".repeat(Math.max(1, 40 - label.length));
  console.log(`[${stageNum}/${TOTAL_STAGES}] ${label}${dots} ${status}`);
}

function fail(stageNum, label, detail) {
  report(stageNum, label, "FAIL");
  console.log();
  console.log("-".repeat(60));
  console.log(`STAGE ${stageNum} FAILED: ${label}`);
  console.log("-".repeat(60));
  console.log(detail);
  console.log();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// ---------------------------------------------------------------------
// Stage 1: Load fixtures
// ---------------------------------------------------------------------

function stage1LoadFixtures() {
  const collection = loadJson(COLLECTION_PATH);
  const normalizedDeck = loadJson(NORMALIZED_DECK_PATH);
  const rawDeck = loadJson(RAW_DECK_PATH);

  assert(Array.isArray(collection) && collection.length > 0, "collection must be a non-empty array");
  assert(normalizedDeck && "mainboard" in normalizedDeck, "normalized deck must have a mainboard");
  assert(rawDeck && "boards" in rawDeck, "raw deck must have a boards object");

  return { collection, normalizedDeck, rawDeck };
}

// ---------------------------------------------------------------------
// Stage 2: Run calculateDeckCost() for every strategy
// ---------------------------------------------------------------------

function stage2RunEngine(collection, normalizedDeck, rawDeck) {
  const results = {};
  for (const strategy of ["same", "cheapest", "most_expensive"]) {
    results[strategy] = calculateDeckCost({
      collection,
      normalizedDeck,
      rawDeck,
      pricingStrategy: strategy,
      includeCommander: true,
    });
  }

  const requiredValues = new Set(Object.values(results).map((r) => r.required));
  const ownedValues = new Set(Object.values(results).map((r) => r.owned));
  const missingValues = new Set(Object.values(results).map((r) => r.missing));

  assert(requiredValues.size === 1, "required differs across pricing strategies");
  assert(ownedValues.size === 1, "owned differs across pricing strategies");
  assert(missingValues.size === 1, "missing differs across pricing strategies");

  return results;
}

// ---------------------------------------------------------------------
// Stage 3: Validate required/owned/missing
// ---------------------------------------------------------------------

function stage3ValidateMatching(results) {
  const anyResult = results.cheapest;

  assert(anyResult.required === 100, `expected required == 100, got ${anyResult.required}`);
  assert(anyResult.owned === 68, `expected owned == 68, got ${anyResult.owned}`);
  assert(anyResult.missing === 32, `expected missing == 32, got ${anyResult.missing}`);
}

// ---------------------------------------------------------------------
// Stage 4: Validate pricing totals
// ---------------------------------------------------------------------

function stage4ValidatePrices(results) {
  for (const [strategy, expectedCents] of Object.entries(EXPECTED_TOTALS_CENTS)) {
    const result = results[strategy];
    assert(
      result.costCents === expectedCents,
      `strategy ${strategy}: expected ${formatCents(expectedCents)}, got ${formatCents(result.costCents)}`
    );
    assert(
      result.pricedQuantity === 32,
      `strategy ${strategy}: expected pricedQuantity == 32, got ${result.pricedQuantity}`
    );
    assert(
      result.unpricedQuantity === 0,
      `strategy ${strategy}: expected unpricedQuantity == 0, got ${result.unpricedQuantity}`
    );
  }
}

// ---------------------------------------------------------------------
// Stage 5: Behavioral distinction between strategies
// ---------------------------------------------------------------------

function stage5ValidateBehavior(results) {
  const sameCents = results.same.costCents;
  const cheapestCents = results.cheapest.costCents;
  const mostExpensiveCents = results.most_expensive.costCents;

  assert(cheapestCents <= sameCents && sameCents <= mostExpensiveCents, "expected cheapest <= same <= most_expensive");
  assert(cheapestCents < sameCents, "expected cheapest strictly less than same for this fixture");
  assert(sameCents < mostExpensiveCents, "expected same strictly less than most_expensive for this fixture");

  const sameByName = new Map(results.same.selections.map((s) => [s.cardName, s]));
  const cheapestByName = new Map(results.cheapest.selections.map((s) => [s.cardName, s]));

  const changedCards = [];
  for (const [name, sameSel] of sameByName) {
    const cheapestSel = cheapestByName.get(name);
    if (!cheapestSel) continue;
    if (sameSel.finish !== cheapestSel.finish || sameSel.unitPriceCents !== cheapestSel.unitPriceCents) {
      changedCards.push(name);
    }
  }

  assert(
    changedCards.length > 0,
    "expected at least one card to select a different printing/treatment between 'same' and 'cheapest'"
  );

  const expectedExamples = new Set(["Smoke Bomb", "Wake the Dead"]);
  const overlap = changedCards.filter((name) => expectedExamples.has(name));
  assert(
    overlap.length > 0,
    `expected known fixture cards [Smoke Bomb, Wake the Dead] among changed cards; got ${changedCards}`
  );
}

// ---------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------

function main() {
  console.log("=".repeat(60));
  console.log("MOXFIELD DECK COST ENGINE - INTEGRATION TEST (JS port)");
  console.log("=".repeat(60));
  console.log();

  const stages = [
    ["Loading fixtures", 1],
    ["Running engine (3 strategies)", 2],
    ["Validating matching totals", 3],
    ["Validating price totals", 4],
    ["Validating strategy behavior", 5],
  ];

  let results = {};
  let label, num;

  try {
    [label, num] = stages[0];
    const { collection, normalizedDeck, rawDeck } = stage1LoadFixtures();
    report(num, label, "PASS");

    [label, num] = stages[1];
    results = stage2RunEngine(collection, normalizedDeck, rawDeck);
    report(num, label, "PASS");

    [label, num] = stages[2];
    stage3ValidateMatching(results);
    report(num, label, "PASS");

    [label, num] = stages[3];
    stage4ValidatePrices(results);
    report(num, label, "PASS");

    [label, num] = stages[4];
    stage5ValidateBehavior(results);
    report(num, label, "PASS");
  } catch (err) {
    fail(num, label, err.message);
    process.exit(1);
  }

  const anyResult = results.cheapest;

  console.log();
  console.log("-".repeat(60));
  console.log("INTEGRATION RESULTS");
  console.log("-".repeat(60));
  console.log(`Required cards:       ${anyResult.required}`);
  console.log(`Owned cards:          ${anyResult.owned}`);
  console.log(`Missing cards:        ${anyResult.missing}`);
  console.log();
  console.log(`Same:              ${formatCents(results.same.costCents)}`);
  console.log(`Cheapest:          ${formatCents(results.cheapest.costCents)}`);
  console.log(`Most expensive:    ${formatCents(results.most_expensive.costCents)}`);
  console.log();
  console.log("=".repeat(60));
  console.log("INTEGRATION TEST PASSED");
  console.log("=".repeat(60));
  process.exit(0);
}

main();
