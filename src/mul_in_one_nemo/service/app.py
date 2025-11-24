"""FastAPI application entrypoint for Mul-in-One backend service."""

from __future__ import annotations

from fastapi import FastAPI

from mul_in_one_nemo.service.routers import personas, sessions


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Mul-in-One Backend", version="0.1.0")

    app.include_router(sessions.router, prefix="/api")
    app.include_router(personas.router, prefix="/api")

    return app
