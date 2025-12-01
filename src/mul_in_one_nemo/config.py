"""Runtime settings and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from .api_config import APIConfiguration, load_api_configuration

# These settings are now managed in .envrc and loaded directly.
# DEFAULT_NIM_MODEL = ""
# DEFAULT_NIM_BASE_URL = ""
# DEFAULT_MAX_AGENTS_PER_TURN = 2
# DEFAULT_MEMORY_WINDOW = 8
# DEFAULT_TEMPERATURE = 0.4


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser()
    return default


@dataclass(slots=True)
class Settings:
    """Application-level configuration loaded from env."""

    # Core required fields
    database_url: str

    # Optional runtime defaults (can be overridden by user data in DB)
    max_agents_per_turn: int = 2
    memory_window: int = 8
    temperature: float = 0.4
    # Max conversation exchanges per user message (rounds)
    max_exchanges_per_turn: int = 8

    # Legacy fields for backward compatibility (optional)
    persona_file: Path | None = None
    nim_model: str = ""
    nim_base_url: str = ""
    nim_api_key: str = ""
    api_config_path: Path | None = None
    api_configuration: APIConfiguration | None = None
    redis_url: str | None = None
    encryption_key: str = ""

    @classmethod
    def from_env(cls, persona_file: str | None = None, api_config_file: str | None = None) -> "Settings":
        # Load required settings from environment variables
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("Missing required environment variable: DATABASE_URL")

        # Load optional persona file (for backward compatibility)
        persona_path_str = persona_file or os.environ.get("MUL_IN_ONE_PERSONAS")
        persona_path: Path | None = None
        if persona_path_str:
            persona_path = Path(persona_path_str).expanduser()

        # Load optional API config (for backward compatibility)
        config_path_str = api_config_file or os.environ.get("MUL_IN_ONE_API_CONFIG")
        api_config_path: Path | None = None
        api_configuration: APIConfiguration | None = None
        default_entry = None
        if config_path_str:
            api_config_path = Path(config_path_str).expanduser()
            if api_config_path.exists():
                api_configuration = load_api_configuration(api_config_path)
                default_entry = api_configuration.resolve_default()

        # Legacy model configuration (optional, can be empty)
        nim_model = os.environ.get("MUL_IN_ONE_NIM_MODEL", "")
        if not nim_model and default_entry:
            nim_model = default_entry.model or ""

        nim_base_url = os.environ.get("MUL_IN_ONE_NIM_BASE_URL", "")
        if not nim_base_url and default_entry:
            nim_base_url = default_entry.base_url or ""

        nim_api_key = os.environ.get("MUL_IN_ONE_NEMO_API_KEY") or os.environ.get("NVIDIA_API_KEY") or ""
        if not nim_api_key and default_entry and default_entry.api_key:
            nim_api_key = default_entry.api_key

        # Runtime defaults with fallbacks
        temperature_str = os.environ.get("MUL_IN_ONE_TEMPERATURE")
        if temperature_str:
            temperature = float(temperature_str)
        elif default_entry and default_entry.temperature is not None:
            temperature = default_entry.temperature
        else:
            temperature = 0.4  # Default

        max_agents_str = os.environ.get("MUL_IN_ONE_MAX_AGENTS")
        max_agents = int(max_agents_str) if max_agents_str else 2

        memory_window_str = os.environ.get("MUL_IN_ONE_MEMORY_WINDOW")
        memory_window = int(memory_window_str) if memory_window_str else 8
        
        max_exchanges_str = os.environ.get("MUL_IN_ONE_MAX_EXCHANGES")
        max_exchanges = int(max_exchanges_str) if max_exchanges_str else 8
        
        redis_url = os.environ.get("REDIS_URL")
        encryption_key = os.environ.get("MUL_IN_ONE_ENCRYPTION_KEY", "")
        
        return cls(
            database_url=database_url,
            persona_file=persona_path,
            nim_model=nim_model,
            nim_base_url=nim_base_url,
            nim_api_key=nim_api_key,
            max_agents_per_turn=max_agents,
            memory_window=memory_window,
            temperature=temperature,
            max_exchanges_per_turn=max_exchanges,
            api_config_path=api_config_path,
            api_configuration=api_configuration,
            redis_url=redis_url,
            encryption_key=encryption_key,
        )
