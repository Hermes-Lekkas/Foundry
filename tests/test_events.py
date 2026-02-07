# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Tests for the async EventBus."""

import asyncio
import pytest
from foundry.shared.events import EventBus, EventType, Event


@pytest.fixture
def bus():
    return EventBus()


@pytest.mark.asyncio
async def test_subscribe_and_publish(bus):
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.SYSTEM_READY, handler)
    await bus.emit(EventType.SYSTEM_READY, {"test": True})

    assert len(received) == 1
    assert received[0].type == EventType.SYSTEM_READY
    assert received[0].data["test"] is True


@pytest.mark.asyncio
async def test_subscribe_all(bus):
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe_all(handler)
    await bus.emit(EventType.SYSTEM_READY)
    await bus.emit(EventType.TRAIN_START)

    assert len(received) == 2


@pytest.mark.asyncio
async def test_unsubscribe(bus):
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.SYSTEM_READY, handler)
    bus.unsubscribe(EventType.SYSTEM_READY, handler)
    await bus.emit(EventType.SYSTEM_READY)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_history(bus):
    await bus.emit(EventType.TRAIN_STEP, {"step": 1})
    await bus.emit(EventType.TRAIN_STEP, {"step": 2})

    recent = bus.recent(10)
    assert len(recent) == 2
    assert recent[0].data["step"] == 1
    assert recent[1].data["step"] == 2


@pytest.mark.asyncio
async def test_error_in_subscriber_doesnt_crash(bus):
    async def bad_handler(event):
        raise ValueError("oops")

    async def good_handler(event):
        pass

    bus.subscribe(EventType.SYSTEM_READY, bad_handler)
    bus.subscribe(EventType.SYSTEM_READY, good_handler)

    # Should not raise
    await bus.emit(EventType.SYSTEM_READY)


def test_event_types_exist():
    assert EventType.TRAIN_START.value == "train.start"
    assert EventType.DATA_SYNTH_COMPLETE.value == "data.synth.complete"
    assert EventType.VRAM_PROFILE_COMPLETE.value == "vram.profile.complete"
