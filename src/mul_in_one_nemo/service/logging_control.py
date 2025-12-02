from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable

# Supported log levels and defaults
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_LEVEL = "ERROR"
DEFAULT_CLEANUP_SECONDS = 7 * 24 * 60 * 60
MIN_CLEANUP_SECONDS = 10

# Shared logger names that should follow the configured level
WATCHED_LOGGERS = (
    "mul_in_one_nemo",
    "mul_in_one_nemo.service",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "pymilvus",
)
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


@dataclass
class LogSettings:
    """Serializable log configuration."""

    level: str = DEFAULT_LEVEL
    cleanup_enabled: bool = True
    cleanup_interval_seconds: int = DEFAULT_CLEANUP_SECONDS


class LogManager:
    """Centralized logging configurator and maintenance scheduler."""

    def __init__(self, log_file: Path, settings_file: Path) -> None:
        self.log_file = log_file
        self.settings_file = settings_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cleanup_thread: threading.Thread | None = None
        self.settings = self._load_settings()
        self._persist_settings()

    def configure_logging(self) -> None:
        """Ensure handler exists, apply the configured level, and start cleanup."""
        root_logger = logging.getLogger()
        handler = self._ensure_rotating_handler(root_logger)

        # Apply levels to root and watched loggers
        level_value = self._resolve_level(self.settings.level)
        root_logger.setLevel(level_value)
        handler.setLevel(level_value)

        for name in WATCHED_LOGGERS:
            component_logger = logging.getLogger(name)
            component_logger.setLevel(level_value)
            component_logger.propagate = True
            for h in list(component_logger.handlers):
                if h is not handler:
                    component_logger.removeHandler(h)

        for uvicorn_logger_name in UVICORN_LOGGERS:
            uvicorn_logger = logging.getLogger(uvicorn_logger_name)
            uvicorn_logger.propagate = True
            uvicorn_logger.setLevel(level_value)

        self._restart_cleanup_thread()

    def update_settings(
        self,
        *,
        level: str | None = None,
        cleanup_enabled: bool | None = None,
        cleanup_interval_seconds: int | None = None,
    ) -> LogSettings:
        """Update persisted settings and reconfigure loggers/cleanup."""
        with self._lock:
            if level is not None:
                self.settings.level = self._validate_level(level)
            if cleanup_enabled is not None:
                self.settings.cleanup_enabled = cleanup_enabled
            if cleanup_interval_seconds is not None:
                target_interval = max(cleanup_interval_seconds, MIN_CLEANUP_SECONDS)
                will_enable = cleanup_enabled if cleanup_enabled is not None else self.settings.cleanup_enabled
                if target_interval < MIN_CLEANUP_SECONDS and will_enable:
                    raise ValueError(f"cleanup_interval_seconds must be >= {MIN_CLEANUP_SECONDS} seconds")
                self.settings.cleanup_interval_seconds = target_interval

            self._persist_settings()
            # Apply changes
            self.configure_logging()
            return self.settings

    def get_settings(self) -> LogSettings:
        return self.settings

    def cleanup_logs(self) -> None:
        """Truncate active and rotated logs to keep disk usage bounded."""
        with self._lock:
            handler = self._find_file_handler()
            try:
                if handler:
                    handler.acquire()
                    try:
                        handler.close()
                        self._truncate_log_files()
                        handler.stream = handler._open()  # type: ignore[attr-defined]
                    finally:
                        handler.release()
                else:
                    self._truncate_log_files()
            except Exception:
                logging.getLogger(__name__).exception("Failed to cleanup logs")

    # --- Internal helpers -------------------------------------------------
    def _resolve_level(self, level: str) -> int:
        return getattr(logging, self._validate_level(level), logging.ERROR)

    def _validate_level(self, level: str) -> str:
        upper = level.upper()
        if upper not in LOG_LEVELS:
            raise ValueError(f"Unsupported log level: {level}")
        return upper

    def _load_settings(self) -> LogSettings:
        if not self.settings_file.exists():
            return LogSettings()
        try:
            data = json.loads(self.settings_file.read_text())
            level = data.get("level", DEFAULT_LEVEL)
            cleanup_enabled = bool(data.get("cleanup_enabled", True))
            cleanup_interval = int(data.get("cleanup_interval_seconds", DEFAULT_CLEANUP_SECONDS))
            cleanup_interval = max(cleanup_interval, MIN_CLEANUP_SECONDS)
            return LogSettings(
                level=self._validate_level(level),
                cleanup_enabled=cleanup_enabled,
                cleanup_interval_seconds=cleanup_interval,
            )
        except Exception:
            # If parsing fails, fall back to defaults to keep service healthy
            return LogSettings()

    def _persist_settings(self) -> None:
        self.settings_file.write_text(json.dumps(asdict(self.settings), indent=2))

    def _ensure_rotating_handler(self, root_logger: logging.Logger) -> RotatingFileHandler:
        existing = next(
            (
                h
                for h in root_logger.handlers
                if isinstance(h, RotatingFileHandler) and Path(getattr(h, "baseFilename", "")) == self.log_file
            ),
            None,
        )
        if existing:
            return existing

        handler = RotatingFileHandler(self.log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        return handler

    def _find_file_handler(self) -> RotatingFileHandler | None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, RotatingFileHandler) and Path(getattr(handler, "baseFilename", "")) == self.log_file:
                return handler
        return None

    def _truncate_log_files(self) -> None:
        """Truncate the primary log and remove rotated backups."""
        self.log_file.write_text("")
        for rotated in self.log_file.parent.glob(f"{self.log_file.name}.*"):
            try:
                rotated.unlink()
            except FileNotFoundError:
                continue

    def _restart_cleanup_thread(self) -> None:
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_event.set()
            self._cleanup_thread.join(timeout=1)
        self._stop_event.clear()

        if not self.settings.cleanup_enabled:
            return

        interval = max(self.settings.cleanup_interval_seconds, MIN_CLEANUP_SECONDS)

        def _loop() -> None:
            while not self._stop_event.wait(interval):
                self.cleanup_logs()

        self._cleanup_thread = threading.Thread(target=_loop, daemon=True, name="log-cleanup")
        self._cleanup_thread.start()


_LOG_MANAGER: LogManager | None = None


def get_log_manager(log_file: Path | None = None) -> LogManager:
    """Singleton accessor for the process-wide log manager."""
    global _LOG_MANAGER
    if _LOG_MANAGER is not None:
        return _LOG_MANAGER

    resolved_log_file = log_file or Path.cwd() / "logs" / "backend.log"
    settings_file = resolved_log_file.parent / "log_settings.json"
    _LOG_MANAGER = LogManager(resolved_log_file, settings_file)
    return _LOG_MANAGER
