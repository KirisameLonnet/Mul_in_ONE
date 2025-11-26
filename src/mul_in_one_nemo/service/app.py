"""FastAPI application entrypoint for Mul-in-One backend service."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from mul_in_one_nemo.service.routers import personas, sessions, debug


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Mul-in-One Backend", version="0.1.0")

    # Configure application-wide logging to a rotating file
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "backend.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if uvicorn reloads
    existing_file_handler = any(
        isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == log_file_path
        for h in logger.handlers
    )
    if not existing_file_handler:
        file_handler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    app.include_router(sessions.router, prefix="/api")
    app.include_router(personas.router, prefix="/api")
    app.include_router(debug.router, prefix="/api")

    return app
