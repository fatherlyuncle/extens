"""
Collection representation.

Extracted from deck_cost.py's build_collection_index() with no behavior
change: same input shape, same output shape, same edge-case handling.
"""

from __future__ import annotations

from typing import Any


def build_collection_index(collection: Any) -> dict[str, dict[str, Any]]:
    """
    Build a name -> collection-record index from the normalized collection
    (a list of {"name", "total_quantity", "unique_printings": [...]} dicts).
    """
    if not isinstance(collection, list):
        raise TypeError("Normalized collection must be a list.")

    index: dict[str, dict[str, Any]] = {}
    for record in collection:
        if not isinstance(record, dict):
            continue
        name = record.get("name")
        if name:
            index[str(name)] = record
    return index
