"""API configuration loader and persona binding helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import yaml

from .api_bindings import normalize_key, parse_bindings
from .persona import Persona, PersonaAPIConfig


@dataclass(slots=True)
class APIConfigEntry:
    name: str
    base_url: str
    model: str
    api_key: str
    temperature: float | None = None


@dataclass(slots=True)
class APIConfiguration:
    configs: Dict[str, APIConfigEntry]
    default_api: str | None = None
    persona_bindings: Dict[str, str] | None = None

    def resolve_default(self) -> APIConfigEntry | None:
        if self.default_api and self.default_api in self.configs:
            return self.configs[self.default_api]
        return next(iter(self.configs.values()), None)

    def resolve_for_persona(self, persona_identifier: str | None) -> APIConfigEntry | None:
        if not persona_identifier or not self.persona_bindings:
            return None
        key = normalize_key(persona_identifier)
        api_name = self.persona_bindings.get(key)
        if not api_name:
            return None
        return self.configs.get(api_name)


def load_api_configuration(path: Path) -> APIConfiguration:
    if not path.exists():
        raise FileNotFoundError(f"API configuration file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    entries = raw.get("apis")
    if not isinstance(entries, list) or not entries:
        raise ValueError("API configuration must define a non-empty 'apis' list")

    configs: Dict[str, APIConfigEntry] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            raise ValueError("Each API entry requires a 'name'")
        model = entry.get("model")
        if not model:
            raise ValueError(f"API entry '{name}' missing 'model'")
        base_url = entry.get("base_url") or entry.get("provider_url") or entry.get("url")
        if not base_url:
            raise ValueError(f"API entry '{name}' missing 'base_url' or 'provider_url'")
        api_key = entry.get("api_key", "")
        temperature_value = entry.get("temperature")
        temperature = float(temperature_value) if temperature_value is not None else None
        configs[name] = APIConfigEntry(
            name=name,
            base_url=base_url,
            model=model,
            api_key=str(api_key),
            temperature=temperature,
        )

    persona_bindings = parse_bindings(raw.get("persona_bindings"))
    default_api = raw.get("default_api")
    return APIConfiguration(configs=configs, default_api=default_api, persona_bindings=persona_bindings)


def apply_api_bindings(personas: Iterable[Persona], configuration: APIConfiguration) -> None:
    default_entry = configuration.resolve_default()
    for persona in personas:
        binding_entry = None
        if persona.api_binding:
            binding_entry = configuration.configs.get(persona.api_binding)
        if not binding_entry:
            binding_entry = configuration.resolve_for_persona(persona.handle) or configuration.resolve_for_persona(persona.name)
        selected_entry = binding_entry or default_entry
        if not selected_entry:
            continue
        persona.api = _merge_api_config(persona.api, selected_entry)


def _merge_api_config(existing: PersonaAPIConfig | None, entry: APIConfigEntry) -> PersonaAPIConfig:
    if existing is None:
        return PersonaAPIConfig(
            model=entry.model,
            base_url=entry.base_url,
            api_key=entry.api_key,
            temperature=entry.temperature,
        )
    return PersonaAPIConfig(
        model=existing.model or entry.model,
        base_url=existing.base_url or entry.base_url,
        api_key=existing.api_key or entry.api_key,
        temperature=existing.temperature if existing.temperature is not None else entry.temperature,
    )
