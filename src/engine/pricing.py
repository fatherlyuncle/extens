"""
Printing/price catalog and price-selection strategies.

Extracted from deck_cost.py's build_raw_price_catalog(), price_options(),
and select_price() with no behavior change.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return x if x >= 0 else None


def build_raw_price_catalog(
    raw_records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    catalog: dict[str, list[dict[str, Any]]] = {}

    for record in raw_records:
        name = record.get("name")
        if name:
            catalog.setdefault(str(name), []).append(record)

    return catalog


def price_options(record: dict[str, Any]) -> list[dict[str, Any]]:
    prices = record.get("prices", {})
    if not isinstance(prices, dict):
        return []

    result = []

    for finish, field in (
        ("nonFoil", "usd"),
        ("foil", "usd_foil"),
        ("etched", "usd_etched"),
    ):
        value = dec(prices.get(field))
        if value is not None:
            result.append({
                "finish": finish,
                "price_field": field,
                "price": value,
            })

    return result


def select_price(
    records: list[dict[str, Any]],
    strategy: str,
) -> dict[str, Any] | None:
    candidates = []

    for record in records:
        options = price_options(record)
        requested_finish = record.get("finish", "nonFoil")

        if strategy == "same":
            options = [
                x for x in options
                if x["finish"] == requested_finish
            ]

        for option in options:
            candidates.append({**option, "record": record})

    if not candidates:
        return None

    if strategy == "same":
        return candidates[0]
    if strategy == "cheapest":
        return min(candidates, key=lambda x: x["price"])
    if strategy == "most_expensive":
        return max(candidates, key=lambda x: x["price"])

    raise ValueError(f"Unknown price strategy: {strategy}")
