# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""FastAPI Application Factory — The Foundry API server."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from foundry import __version__
from foundry.orchestrator.state import StateManager
from foundry.orchestrator.websocket import ConnectionManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — initialize and teardown resources."""
    logger.info("The Foundry v%s — Initializing", __version__)

    # Initialize state manager
    state = StateManager()
    await state.initialize()
    app.state.state_manager = state

    # Initialize WebSocket connection manager
    app.state.ws_manager = ConnectionManager()

    # Wire EventBus to WebSocket broadcast
    from foundry.shared.events import get_event_bus

    bus = get_event_bus()
    bus.subscribe_all(app.state.ws_manager.broadcast_event)

    logger.info("The Foundry — Ready")
    yield

    # Cleanup
    await state.close()
    logger.info("The Foundry — Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="The Foundry",
        description="Local LLM Training Ecosystem — API Server",
        version=__version__,
        lifespan=lifespan,
    )

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8420"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from foundry.orchestrator.routes.config import router as config_router
    from foundry.orchestrator.routes.data import router as data_router
    from foundry.orchestrator.routes.eval import router as eval_router
    from foundry.orchestrator.routes.health import router as health_router
    from foundry.orchestrator.routes.training import router as training_router
    from foundry.orchestrator.routes.ws import router as ws_router

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(config_router, prefix="/api/config", tags=["config"])
    app.include_router(data_router, prefix="/api/data", tags=["data"])
    app.include_router(training_router, prefix="/api/training", tags=["training"])
    app.include_router(eval_router, prefix="/api/eval", tags=["eval"])
    app.include_router(ws_router, tags=["websocket"])

    return app
