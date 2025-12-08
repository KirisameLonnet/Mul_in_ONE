"""FastAPI application entrypoint for Mul-in-One backend service."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mul_in_one_nemo.auth.routes import router as auth_router
from mul_in_one_nemo.service.routers import personas, sessions, debug, admin
from mul_in_one_nemo.service.logging_control import get_log_manager


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Mul-in-One Backend",
        version="0.1.0",
        docs_url=None,
        redoc_url=None
    )

    # Configure application-wide logging to a rotating file with managed levels/cleanup
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = Path(log_dir) / "backend.log"

    log_manager = get_log_manager(log_file_path)
    log_manager.configure_logging()

    app.include_router(auth_router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(personas.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(debug.router, prefix="/api")

    avatar_dir = Path(os.getenv("PERSONA_AVATAR_DIR", Path.cwd() / "configs" / "persona_avatars"))
    avatar_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/persona-avatars", StaticFiles(directory=avatar_dir), name="persona-avatars")

    return app
