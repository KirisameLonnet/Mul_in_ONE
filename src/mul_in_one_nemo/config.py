"""Runtime settings and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .api_config import APIConfiguration, load_api_configuration

DEFAULT_NIM_MODEL = "meta/llama-3.1-70b-instruct"
DEFAULT_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MAX_AGENTS_PER_TURN = 2
DEFAULT_MEMORY_WINDOW = 8
DEFAULT_TEMPERATURE = 0.4
DEFAULT_PERSONA_FILE = Path("personas/persona.yaml")
DEFAULT_API_CONFIG_FILE = Path("personas/api_configuration.yaml")


@dataclass(slots=True)
class Settings:
    """Application-level configuration loaded from env + persona file."""

    persona_file: Path
    nim_model: str = DEFAULT_NIM_MODEL
    nim_base_url: str = DEFAULT_NIM_BASE_URL
    nim_api_key: str = ""
    max_agents_per_turn: int = DEFAULT_MAX_AGENTS_PER_TURN
    memory_window: int = DEFAULT_MEMORY_WINDOW
    temperature: float = DEFAULT_TEMPERATURE
    api_config_path: Path | None = None
    api_configuration: APIConfiguration | None = None

    @classmethod
    def from_env(cls, persona_file: str | None = None, api_config_file: str | None = None) -> "Settings":
        persona_path_str = persona_file or os.environ.get("MUL_IN_ONE_PERSONAS")
        if persona_path_str:
            persona_path = Path(persona_path_str).expanduser()
        else:
            persona_path = DEFAULT_PERSONA_FILE if DEFAULT_PERSONA_FILE.exists() else Path("personas/persona.yaml")

        api_config_path: Path | None = None
        api_configuration: APIConfiguration | None = None
        default_entry = None
        config_path_str = api_config_file or os.environ.get("MUL_IN_ONE_API_CONFIG")
        if not config_path_str and DEFAULT_API_CONFIG_FILE.exists():
            config_path_str = str(DEFAULT_API_CONFIG_FILE)
        if config_path_str:
            api_config_path = Path(config_path_str).expanduser()
            api_configuration = load_api_configuration(api_config_path)
            default_entry = api_configuration.resolve_default()

        nim_model = os.environ.get("MUL_IN_ONE_NIM_MODEL")
        if not nim_model:
            nim_model = (default_entry.model if default_entry and default_entry.model else DEFAULT_NIM_MODEL)

        nim_base_url = os.environ.get("MUL_IN_ONE_NIM_BASE_URL")
        if not nim_base_url:
            nim_base_url = (default_entry.base_url if default_entry and default_entry.base_url else DEFAULT_NIM_BASE_URL)

        nim_api_key = os.environ.get("MUL_IN_ONE_NEMO_API_KEY") or os.environ.get("NVIDIA_API_KEY")
        if not nim_api_key and default_entry and default_entry.api_key:
            nim_api_key = default_entry.api_key
        nim_api_key = nim_api_key or ""

        temperature_env = os.environ.get("MUL_IN_ONE_TEMPERATURE")
        if temperature_env is not None:
            temperature = float(temperature_env)
        elif default_entry and default_entry.temperature is not None:
            temperature = default_entry.temperature
        else:
            temperature = DEFAULT_TEMPERATURE
        max_agents = int(os.environ.get("MUL_IN_ONE_MAX_AGENTS", DEFAULT_MAX_AGENTS_PER_TURN))
        memory_window = int(os.environ.get("MUL_IN_ONE_MEMORY_WINDOW", DEFAULT_MEMORY_WINDOW))
        return cls(
            persona_file=persona_path,
            nim_model=nim_model,
            nim_base_url=nim_base_url,
            nim_api_key=nim_api_key,
            max_agents_per_turn=max_agents,
            memory_window=memory_window,
            temperature=temperature,
            api_config_path=api_config_path,
            api_configuration=api_configuration,
        )
