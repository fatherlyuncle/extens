#!/usr/bin/env python3
"""
integration_test.py
====================

End-to-end integration test for the Moxfield deck-cost engine's public
API: engine.calculate_deck_cost().

This supersedes the earlier version of this test, which manually chained
deck_cost.py's lower-level functions (build_requirements -> match_deck ->
calculate) together. Now that the engine has been extracted into
src/engine/ behind a single public entry point, the test calls that
entry point directly -- exercising exactly what the eventual browser
integration will call, rather than testing internals that callers won't
touch.

deck_cost.py is kept as the known-good reference implementation. Its
numbers for these fixtures are:

    Required: 100
    Owned:    68
    Missing:  32

    same             $48.68
    cheapest         $48.41
    most_expensive   $87.48

    priced_quantity=32, unpriced_quantity=0 for every strategy

This test requires the new engine to reproduce those numbers exactly.
If it doesn't, that's a real behavioral discrepancy introduced by the
extraction, not something to paper over.

No UI, DOM, or network code is involved here.

Run with:

    python3 test/integration_test.py
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

# src/ is a sibling of test/; add it to the path so `import engine` works
# without needing the package installed.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from engine import calculate_deck_cost  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
MOXFIELD_DIR = BASE_DIR / "moxfield"

COLLECTION_PATH = MOXFIELD_DIR / "collection_normalized.json"
NORMALIZED_DECK_PATH = MOXFIELD_DIR / "testdeck_normalized.json"
RAW_DECK_PATH = MOXFIELD_DIR / "testdeck.json"

TOTAL_STAGES = 6

EXPECTED_TOTALS = {
    "same": Decimal("48.68"),
    "cheapest": Decimal("48.41"),
    "most_expensive": Decimal("87.48"),
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _report(stage_num: int, label: str, status: str) -> None:
    dots = "." * max(1, 40 - len(label))
    print(f"[{stage_num}/{TOTAL_STAGES}] {label}{dots} {status}")


def _fail(stage_num: int, label: str, detail: str) -> None:
    _report(stage_num, label, "FAIL")
    print()
    print("-" * 60)
    print(f"STAGE {stage_num} FAILED: {label}")
    print("-" * 60)
    print(detail)
    print()


# ---------------------------------------------------------------------
# Stage 1: Load fixtures
# ---------------------------------------------------------------------

def stage_1_load_fixtures() -> tuple[Any, dict[str, Any], dict[str, Any]]:
    collection = load_json(COLLECTION_PATH)
    normalized_deck = load_json(NORMALIZED_DECK_PATH)
    raw_deck = load_json(RAW_DECK_PATH)

    assert isinstance(collection, list) and len(collection) > 0
    assert isinstance(normalized_deck, dict) and "mainboard" in normalized_deck
    assert isinstance(raw_deck, dict) and "boards" in raw_deck

    return collection, normalized_deck, raw_deck


# ---------------------------------------------------------------------
# Stage 2: Run calculate_deck_cost() for every strategy
# ---------------------------------------------------------------------

def stage_2_run_engine(
    collection: Any,
    normalized_deck: dict[str, Any],
    raw_deck: dict[str, Any],
) -> dict[str, Any]:
    results = {}
    for strategy in ("same", "cheapest", "most_expensive"):
        result = calculate_deck_cost(
            collection=collection,
            normalized_deck=normalized_deck,
            raw_deck=raw_deck,
            pricing_strategy=strategy,
            include_commander=True,
        )
        results[strategy] = result

    # calculate_deck_cost is deterministic per-strategy w.r.t.
    # required/owned/missing (those don't depend on pricing_strategy at
    # all) -- confirm that's actually true rather than assuming it.
    required_values = {r.required for r in results.values()}
    owned_values = {r.owned for r in results.values()}
    missing_values = {r.missing for r in results.values()}
    assert len(required_values) == 1, "required differs across pricing strategies"
    assert len(owned_values) == 1, "owned differs across pricing strategies"
    assert len(missing_values) == 1, "missing differs across pricing strategies"

    return results


# ---------------------------------------------------------------------
# Stage 3: Validate required/owned/missing
# ---------------------------------------------------------------------

def stage_3_validate_matching(results: dict[str, Any]) -> None:
    any_result = next(iter(results.values()))

    assert any_result.required == 100, f"expected required == 100, got {any_result.required}"
    assert any_result.owned == 68, f"expected owned == 68, got {any_result.owned}"
    assert any_result.missing == 32, f"expected missing == 32, got {any_result.missing}"


# ---------------------------------------------------------------------
# Stage 4: Validate pricing totals
# ---------------------------------------------------------------------

def stage_4_validate_prices(results: dict[str, Any]) -> None:
    for strategy, expected in EXPECTED_TOTALS.items():
        result = results[strategy]
        actual = result.cost.quantize(Decimal("0.01"))
        assert actual == expected, (
            f"strategy {strategy!r}: expected total {expected}, got {actual}"
        )
        assert result.priced_quantity == 32, (
            f"strategy {strategy!r}: expected priced_quantity == 32, "
            f"got {result.priced_quantity}"
        )
        assert result.unpriced_quantity == 0, (
            f"strategy {strategy!r}: expected unpriced_quantity == 0, "
            f"got {result.unpriced_quantity}"
        )


# ---------------------------------------------------------------------
# Stage 5: Behavioral distinction between strategies
# ---------------------------------------------------------------------

def stage_5_validate_behavior(results: dict[str, Any]) -> None:
    same_cost = results["same"].cost
    cheapest_cost = results["cheapest"].cost
    most_expensive_cost = results["most_expensive"].cost

    assert cheapest_cost <= same_cost <= most_expensive_cost
    assert cheapest_cost < same_cost, (
        "expected cheapest strategy to be strictly cheaper than same-printing "
        "strategy for this fixture"
    )
    assert same_cost < most_expensive_cost, (
        "expected same-printing strategy to be strictly cheaper than "
        "most-expensive strategy for this fixture"
    )

    # Confirm at least one card actually changed selected finish/price
    # between "same" and "cheapest" -- otherwise the strategies wouldn't
    # really be exercised as distinct code paths.
    same_by_name = {s.card_name: s for s in results["same"].selections}
    cheapest_by_name = {s.card_name: s for s in results["cheapest"].selections}

    changed_cards = [
        name
        for name, same_sel in same_by_name.items()
        if name in cheapest_by_name
        and (
            same_sel.finish != cheapest_by_name[name].finish
            or same_sel.unit_price != cheapest_by_name[name].unit_price
        )
    ]

    assert changed_cards, (
        "expected at least one card to select a different printing/treatment "
        "between the 'same' and 'cheapest' strategies"
    )

    expected_examples = {"Smoke Bomb", "Wake the Dead"}
    assert expected_examples & set(changed_cards), (
        f"expected known fixture cards {sorted(expected_examples)} to be among "
        f"the cards that change printing between strategies; got {changed_cards}"
    )


# ---------------------------------------------------------------------
# Stage 6: Cross-check against the deck_cost.py reference implementation
# ---------------------------------------------------------------------

def stage_6_cross_check_reference() -> None:
    """
    Import the original deck_cost.py and confirm its module-level
    functions still produce the same reference numbers this test just
    validated against the new engine. This is a guardrail against the
    reference fixture itself silently changing out from under us.
    """
    import contextlib
    import io

    sys.path.insert(0, str(BASE_DIR))
    import deck_cost as reference  # noqa: E402

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        collection = reference.load_json(reference.COLLECTION_PATH)
        normalized_deck = reference.load_json(reference.NORMALIZED_DECK_PATH)
        raw_deck = reference.load_json(reference.RAW_DECK_PATH)

        raw_records = reference.extract_deck_records(raw_deck)
        collection_index = reference.build_collection_index(collection)
        requirements = reference.build_requirements(normalized_deck)
        matches = reference.match_deck(requirements, collection_index)
        catalog = reference.build_raw_price_catalog(raw_records)

        ref_required = sum(m["required"] for m in matches)
        ref_owned = sum(m["owned"] for m in matches)
        ref_missing = sum(m["missing"] for m in matches)

        ref_totals = {}
        for strategy in ("same", "cheapest", "most_expensive"):
            total, priced, unpriced = reference.calculate(matches, catalog, strategy)
            ref_totals[strategy] = (total, priced, unpriced)

    assert ref_required == 100 and ref_owned == 68 and ref_missing == 32, (
        "reference implementation itself no longer matches the documented "
        "baseline -- check the fixtures before trusting this test"
    )
    for strategy, expected in EXPECTED_TOTALS.items():
        total, priced, unpriced = ref_totals[strategy]
        assert total.quantize(Decimal("0.01")) == expected
        assert priced == 32 and unpriced == 0


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("MOXFIELD DECK COST ENGINE - INTEGRATION TEST")
    print("(testing src/engine.calculate_deck_cost public API)")
    print("=" * 60)
    print()

    results: dict[str, Any] = {}

    stages = [
        ("Loading fixtures", 1),
        ("Running engine (3 strategies)", 2),
        ("Validating matching totals", 3),
        ("Validating price totals", 4),
        ("Validating strategy behavior", 5),
        ("Cross-checking reference impl", 6),
    ]

    try:
        label, num = stages[0]
        collection, normalized_deck, raw_deck = stage_1_load_fixtures()
        _report(num, label, "PASS")

        label, num = stages[1]
        results = stage_2_run_engine(collection, normalized_deck, raw_deck)
        _report(num, label, "PASS")

        label, num = stages[2]
        stage_3_validate_matching(results)
        _report(num, label, "PASS")

        label, num = stages[3]
        stage_4_validate_prices(results)
        _report(num, label, "PASS")

        label, num = stages[4]
        stage_5_validate_behavior(results)
        _report(num, label, "PASS")

        label, num = stages[5]
        stage_6_cross_check_reference()
        _report(num, label, "PASS")

    except AssertionError as exc:
        _fail(num, label, str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - surfacing any pipeline error
        _fail(num, label, f"{type(exc).__name__}: {exc}")
        return 1

    any_result = results["cheapest"]

    print()
    print("-" * 60)
    print("INTEGRATION RESULTS")
    print("-" * 60)
    print(f"Required cards:       {any_result.required}")
    print(f"Owned cards:          {any_result.owned:>4}")
    print(f"Missing cards:        {any_result.missing:>4}")
    print()
    print(f"Same:              ${results['same'].cost:.2f}")
    print(f"Cheapest:          ${results['cheapest'].cost:.2f}")
    print(f"Most expensive:    ${results['most_expensive'].cost:.2f}")
    print()
    print("=" * 60)
    print("INTEGRATION TEST PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
