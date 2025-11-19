"""Shared helpers for persona/API binding normalization."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple


def normalize_key(value: str) -> str:
    return value.strip().lower()


def _iter_binding_items(raw: object) -> Iterable[Tuple[str, str]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        return [(str(persona), str(api_name)) for persona, api_name in raw.items() if persona and api_name]
    if isinstance(raw, list):
        pairs = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            persona = entry.get("persona")
            api_name = entry.get("api")
            if persona and api_name:
                pairs.append((str(persona), str(api_name)))
        return pairs
    return []


def parse_bindings(raw: object) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for persona, api_name in _iter_binding_items(raw):
        mapping[normalize_key(persona)] = api_name
    return mapping
