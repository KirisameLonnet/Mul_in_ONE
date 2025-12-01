"""FastAPI application entrypoint for Mul-in-One backend service."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from mul_in_one_nemo.service.routers import personas, sessions, debug


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Mul-in-One Backend",
        version="0.1.0",
        docs_url=None,
        redoc_url=None
    )

    # Configure application-wide logging to a rotating file
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "backend.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if uvicorn reloads
    file_handler: RotatingFileHandler | None = None
    existing_file_handler = next(
        (
            h
            for h in root_logger.handlers
            if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == log_file_path
        ),
        None,
    )
    if existing_file_handler:
        file_handler = existing_file_handler
    else:
        file_handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Ensure important subsystems propagate to the shared handler
    watched_loggers = (
        "mul_in_one_nemo",
        "mul_in_one_nemo.service",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "pymilvus",
    )
    for name in watched_loggers:
        component_logger = logging.getLogger(name)
        component_logger.setLevel(logging.INFO)
        component_logger.propagate = True
        # Remove console-only handlers added by dependencies to avoid stdout-only logs
        for handler in list(component_logger.handlers):
            if handler is not file_handler:
                component_logger.removeHandler(handler)

    # Capture uvicorn access logs as well
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(logging.INFO)

    app.include_router(sessions.router, prefix="/api")
    app.include_router(personas.router, prefix="/api/personas")
    app.include_router(debug.router, prefix="/api")

    return app
