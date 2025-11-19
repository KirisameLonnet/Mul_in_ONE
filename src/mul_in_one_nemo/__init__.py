"""Mul-in-One NeMo integration package."""

from .config import Settings

try:  # pragma: no cover - optional dependency during tests
    from .runtime import MultiAgentRuntime
except (ModuleNotFoundError, ImportError):  # ImportError if nat extras missing
    MultiAgentRuntime = None  # type: ignore[assignment]

__all__ = ["Settings", "MultiAgentRuntime"]
