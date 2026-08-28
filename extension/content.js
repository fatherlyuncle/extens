/**
 * content.js
 * ----------
 * Fetches the live deck for the current Moxfield page and calculates
 * its missing-card cost against a bundled collection snapshot, using
 * the same engine (src/engine_js/) and deck adapter
 * (src/adapters_js/moxfieldDeck.js) verified throughout this
 * project's test suite. Exposed on `window.MoxfieldEngine` by
 * engine.bundle.js, which is loaded before this script (see
 * manifest.json's content_scripts order).
 *
 * SCOPE / KNOWN LIMITATION: the collection data bundled here
 * (data/collection_normalized.json) is a static snapshot taken at
 * build time, NOT a live fetch of the user's actual current
 * collection. Live, authenticated collection fetching is deferred --
 * Moxfield's collection endpoint requires a real logged-in browser
 * session, which is a separate problem from what this script proves.
 * Results will drift from the user's real collection as it changes
 * until that's implemented. This is a known, temporary limitation,
 * not a bug.
 */

(function () {
  "use strict";

  const BADGE_ID = "moxfield-deckcost-badge";
  let cachedCollection = null;

  function getOrCreateBadge() {
    let badge = document.getElementById(BADGE_ID);
    if (badge) return badge;

    badge = document.createElement("div");
    badge.id = BADGE_ID;
    badge.style.cssText = [
      "position: fixed",
      "bottom: 16px",
      "right: 16px",
      "z-index: 2147483647",
      "background: #1e2327",
      "color: #ffffff",
      "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      "font-size: 13px",
      "line-height: 1.5",
      "padding: 10px 14px",
      "border-radius: 8px",
      "box-shadow: 0 2px 12px rgba(0,0,0,0.35)",
      "max-width: 300px",
      "border: 1px solid #3a3f44",
      "white-space: pre-wrap",
    ].join(";");

    document.documentElement.appendChild(badge);
    return badge;
  }

  function setBadge(message, isError) {
    const badge = getOrCreateBadge();
    badge.style.borderColor = isError ? "#c0392b" : "#2ecc71";
    badge.textContent = message;
  }

  function extractDeckIdFromUrl() {
    // Matches /decks/{deckId} or /decks/{deckId}-{slug}
    const match = window.location.pathname.match(/\/decks\/([^/]+)/);
    return match ? match[1] : null;
  }

  async function loadBundledCollection() {
    if (cachedCollection) return cachedCollection;

    const url = chrome.runtime.getURL("data/collection_normalized.json");
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load bundled collection snapshot: HTTP ${response.status}`);
    }
    cachedCollection = await response.json();
    return cachedCollection;
  }

  async function fetchLiveDeck(deckId) {
    const url = `https://api2.moxfield.com/v3/decks/all/${deckId}`;
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) {
      throw new Error(`Deck fetch failed: HTTP ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    if (!data || typeof data !== "object" || !data.boards) {
      throw new Error('Unexpected deck response shape (missing "boards")');
    }
    return data;
  }

  async function run() {
    const deckId = extractDeckIdFromUrl();
    if (!deckId) return; // Not a recognizable deck page URL.

    if (!window.MoxfieldEngine) {
      setBadge("Moxfield Deck-Cost Assistant\nERROR: engine bundle did not load", true);
      return;
    }

    const { calculateDeckCost, formatCents, normalizeDeck, validateNormalizedDeck } = window.MoxfieldEngine;

    setBadge("Moxfield Deck-Cost Assistant\nFetching live deck data...", false);

    let rawDeck;
    try {
      rawDeck = await fetchLiveDeck(deckId);
    } catch (err) {
      setBadge(`Deck fetch failed\n${err.message}`, true);
      return;
    }

    let collection;
    try {
      collection = await loadBundledCollection();
    } catch (err) {
      setBadge(`Collection load failed\n${err.message}`, true);
      return;
    }

    let normalizedDeck;
    try {
      normalizedDeck = normalizeDeck(rawDeck);
      validateNormalizedDeck(rawDeck, normalizedDeck);
    } catch (err) {
      setBadge(`Deck normalization failed\n${err.message}`, true);
      return;
    }

    let result;
    try {
      result = calculateDeckCost({
        collection,
        normalizedDeck,
        rawDeck,
        pricingStrategy: "cheapest",
      });
    } catch (err) {
      setBadge(`Cost calculation failed\n${err.message}`, true);
      return;
    }

    setBadge(
      `Moxfield Deck-Cost Assistant\n` +
        `${rawDeck.name || "Unnamed deck"} (${rawDeck.format || "?"})\n` +
        `\n` +
        `Required: ${result.required}   Owned: ${result.owned}   Missing: ${result.missing}\n` +
        `Cost to complete (cheapest): ${formatCents(result.costCents)}\n` +
        `\n` +
        `(vs. bundled collection snapshot, not live)`,
      false
    );
  }

  run();
})();
