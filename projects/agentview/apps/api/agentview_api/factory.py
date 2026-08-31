from __future__ import annotations

from fastapi import FastAPI

from .app import app


def create_app() -> FastAPI:
    return app
