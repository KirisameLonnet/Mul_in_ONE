from __future__ import annotations

import os
from collections import deque
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from mul_in_one_nemo.auth import current_superuser
from mul_in_one_nemo.service.logging_control import (
    LOG_LEVELS,
    MIN_CLEANUP_SECONDS,
    get_log_manager,
)

router = APIRouter(prefix="/debug", tags=["debug"])

LOG_FILE_RELATIVE = os.path.join("logs", "backend.log")
_LEVEL_ORDER = {name: index for index, name in enumerate(LOG_LEVELS)}
log_manager = get_log_manager()


class LogSettingsResponse(BaseModel):
    level: str
    cleanup_enabled: bool
    cleanup_interval_seconds: int


class UpdateLogSettingsRequest(BaseModel):
    level: str | None = Field(default=None)
    cleanup_enabled: bool | None = Field(default=None)
    cleanup_interval_seconds: int | None = Field(default=None, ge=MIN_CLEANUP_SECONDS)


def _line_meets_level(line: str, min_level: str | None) -> bool:
    if min_level is None:
        return True
    tokens = line.split()
    if len(tokens) < 2:
        return True
    level_name = tokens[1].upper()
    return _LEVEL_ORDER.get(level_name, 0) >= _LEVEL_ORDER[min_level]


def _normalize_level(level: str | None) -> str | None:
    if level is None:
        return None
    upper = level.upper()
    if upper not in LOG_LEVELS:
        raise HTTPException(status_code=400, detail=f"Unsupported log level: {level}")
    return upper


def _read_tail_lines(file_path: str, max_lines: int, min_level: str | None) -> List[str]:
    if not os.path.exists(file_path):
        return ["<log file not found>"]
    selected: deque[str] = deque(maxlen=max_lines)
    try:
        with open(file_path, "r", errors="replace") as f:
            for raw_line in f:
                line = raw_line.rstrip("\n")
                if _line_meets_level(line, min_level):
                    selected.append(line)
    except Exception as e:  # pragma: no cover - defensive read path
        return [f"<error reading log file: {e}>"]
    return list(selected)


@router.get("/logs")
async def get_logs(
    lines: int = Query(default=500, ge=1, le=5000),
    level: str | None = Query(default=None),
):
    """
    Return the last N lines from the backend log file with optional level filtering.
    """
    normalized_level = _normalize_level(level)
    log_path = os.path.join(os.getcwd(), LOG_FILE_RELATIVE)
    tail = _read_tail_lines(log_path, lines, normalized_level)
    current_settings = log_manager.get_settings()
    effective_level = normalized_level or current_settings.level
    return {
        "path": LOG_FILE_RELATIVE,
        "lines": tail,
        "count": len(tail),
        "level": effective_level,
    }


@router.get("/log-settings", response_model=LogSettingsResponse)
async def get_log_settings():
    """Return persisted log configuration."""
    settings = log_manager.get_settings()
    return LogSettingsResponse(**settings.__dict__)


@router.patch("/log-settings", response_model=LogSettingsResponse)
async def update_log_settings(
    payload: UpdateLogSettingsRequest,
    _: object = Depends(current_superuser),
):
    """Update log level and cleanup configuration (admin only)."""
    try:
        settings = log_manager.update_settings(
            level=payload.level,
            cleanup_enabled=payload.cleanup_enabled,
            cleanup_interval_seconds=payload.cleanup_interval_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return LogSettingsResponse(**settings.__dict__)


@router.post("/logs/cleanup", response_model=LogSettingsResponse)
async def trigger_log_cleanup(_: object = Depends(current_superuser)):
    """Trigger an immediate cleanup of backend log files (admin only)."""
    log_manager.cleanup_logs()
    settings = log_manager.get_settings()
    return LogSettingsResponse(**settings.__dict__)
