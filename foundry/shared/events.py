# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Async EventBus — Inter-engine communication for The Foundry.

Enables decoupled communication between Data Engine, Training Core,
Evaluator, and Orchestrator without circular imports.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All event types flowing through The Foundry."""

    # System
    SYSTEM_READY = "system.ready"
    SYSTEM_ERROR = "system.error"

    # VRAM
    VRAM_PROFILE_START = "vram.profile.start"
    VRAM_PROFILE_COMPLETE = "vram.profile.complete"
    VRAM_SWAP_START = "vram.swap.start"
    VRAM_SWAP_COMPLETE = "vram.swap.complete"

    # Data Engine
    DATA_SYNTH_START = "data.synth.start"
    DATA_SYNTH_PROGRESS = "data.synth.progress"
    DATA_SYNTH_COMPLETE = "data.synth.complete"
    DATA_TRAJECTORY_STEP = "data.trajectory.step"

    # Training
    TRAIN_START = "train.start"
    TRAIN_STEP = "train.step"
    TRAIN_EPOCH = "train.epoch"
    TRAIN_LOSS = "train.loss"
    TRAIN_COMPLETE = "train.complete"
    TRAIN_CHECKPOINT = "train.checkpoint"

    # Evaluation
    EVAL_START = "eval.start"
    EVAL_PROGRESS = "eval.progress"
    EVAL_COMPLETE = "eval.complete"

    # Sandbox
    SANDBOX_EXEC_START = "sandbox.exec.start"
    SANDBOX_EXEC_COMPLETE = "sandbox.exec.complete"


@dataclass
class Event:
    """An event flowing through the EventBus."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "unknown"


# Subscriber type: async callable that takes an Event
Subscriber = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async publish-subscribe event bus for inter-engine communication."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Subscriber]] = defaultdict(list)
        self._global_subscribers: list[Subscriber] = []
        self._history: list[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: EventType, callback: Subscriber) -> None:
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Subscriber) -> None:
        """Subscribe to all events (used by WebSocket broadcaster)."""
        self._global_subscribers.append(callback)

    def unsubscribe(self, event_type: EventType, callback: Subscriber) -> None:
        """Remove a subscription."""
        subs = self._subscribers[event_type]
        if callback in subs:
            subs.remove(callback)

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        targets = self._subscribers.get(event.type, []) + self._global_subscribers
        for callback in targets:
            try:
                await callback(event)
            except Exception:
                logger.exception("Error in event subscriber for %s", event.type)

    async def emit(
        self, event_type: EventType, data: dict[str, Any] | None = None, source: str = "system"
    ) -> None:
        """Convenience: create and publish an event in one call."""
        await self.publish(Event(type=event_type, data=data or {}, source=source))

    def recent(self, n: int = 50) -> list[Event]:
        """Get the N most recent events."""
        return self._history[-n:]


# Singleton
_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global EventBus singleton."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
