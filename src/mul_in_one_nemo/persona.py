"""Persona models and loaders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml

@dataclass(slots=True)
class Persona:
    name: str
    handle: str
    prompt: str
    tone: str = "neutral"
    proactivity: float = 0.5
    catchphrases: List[str] | None = None
    api: "PersonaAPIConfig" | None = None
    api_binding: str | None = None

    def system_prompt(self) -> str:
        tagline = f"语气倾向：{self.tone}" if self.tone else ""
        catch = "；".join(self.catchphrases or [])
        tail = f"常用语：{catch}" if catch else ""
        return f"{self.prompt}\n{tagline}\n{tail}".strip()


@dataclass(slots=True)
class PersonaAPIConfig:
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = None


@dataclass(slots=True)
class PersonaSettings:
    personas: List[Persona]
    max_agents_per_turn: int
    memory_window: int


def load_personas(path: Path) -> PersonaSettings:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    personas: List[Persona] = []
    for raw in data.get("personas", []):
        api_field = raw.get("api")
        binding_name = raw.get("api_binding")
        api_config = None
        if isinstance(api_field, dict) and api_field:
            api_config = PersonaAPIConfig(
                model=api_field.get("model"),
                base_url=api_field.get("base_url"),
                api_key=api_field.get("api_key"),
                temperature=float(api_field.get("temperature")) if api_field.get("temperature") is not None else None,
            )
        elif isinstance(api_field, str):
            binding_name = binding_name or api_field

        binding_clean = binding_name.strip() if isinstance(binding_name, str) else None

        personas.append(
            Persona(
                name=raw["name"],
                handle=raw.get("handle", raw["name"].lower()),
                prompt=raw.get("prompt", ""),
                tone=raw.get("tone", "neutral"),
                proactivity=float(raw.get("proactivity", 0.5)),
                catchphrases=raw.get("catchphrases"),
                api=api_config,
                api_binding=binding_clean,
            )
        )
    settings = data.get("settings", {})
    return PersonaSettings(
        personas=personas,
        max_agents_per_turn=settings.get("max_agents_per_turn", 2),
        memory_window=settings.get("memory_window", 8),
    )
