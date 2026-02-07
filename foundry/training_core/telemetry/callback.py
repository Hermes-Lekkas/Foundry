# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Foundry Trainer Callback — Bridges HuggingFace Trainer to EventBus.

Streams training metrics (loss, learning rate, VRAM usage, step progress)
to the EventBus, which forwards to WebSocket clients for real-time dashboards.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FoundryCallback:
    """HuggingFace TrainerCallback that emits events to the Foundry EventBus.

    Works with SFTTrainer, DPOTrainer, and GRPOTrainer.
    """

    def __init__(self) -> None:
        self._start_time: float = 0
        self._step_count: int = 0

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event to the EventBus (sync-safe)."""
        try:
            from foundry.shared.events import EventType, get_event_bus

            bus = get_event_bus()
            et = EventType(event_type)

            # Try to use the running event loop, or create one
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bus.emit(et, data, source="training"))
            except RuntimeError:
                asyncio.run(bus.emit(et, data, source="training"))
        except Exception:
            logger.debug("Failed to emit event %s", event_type, exc_info=True)

    def _get_vram_info(self) -> dict[str, Any]:
        """Get current VRAM usage."""
        try:
            import torch

            if torch.cuda.is_available():
                return {
                    "vram_used_mb": torch.cuda.memory_allocated() // (1024 * 1024),
                    "vram_reserved_mb": torch.cuda.memory_reserved() // (1024 * 1024),
                    "vram_peak_mb": torch.cuda.max_memory_allocated() // (1024 * 1024),
                }
        except Exception:
            pass
        return {}

    def on_train_begin(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        self._start_time = time.time()
        self._emit("train.start", {
            "total_steps": state.max_steps,
            "num_epochs": args.num_train_epochs,
            "batch_size": args.per_device_train_batch_size,
            "learning_rate": args.learning_rate,
            **self._get_vram_info(),
        })

    def on_log(self, args: Any, state: Any, control: Any, logs: dict | None = None, **kwargs: Any) -> None:
        if logs is None:
            return
        self._emit("train.step", {
            "step": state.global_step,
            "total_steps": state.max_steps,
            "epoch": state.epoch,
            "loss": logs.get("loss"),
            "learning_rate": logs.get("learning_rate"),
            "grad_norm": logs.get("grad_norm"),
            "elapsed_seconds": time.time() - self._start_time,
            **self._get_vram_info(),
        })

        if "loss" in logs:
            self._emit("train.loss", {
                "step": state.global_step,
                "loss": logs["loss"],
            })

    def on_epoch_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        self._emit("train.epoch", {
            "epoch": state.epoch,
            "step": state.global_step,
        })

    def on_save(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        self._emit("train.checkpoint", {
            "step": state.global_step,
            "output_dir": args.output_dir,
        })

    def on_train_end(self, args: Any, state: Any, control: Any, **kwargs: Any) -> None:
        elapsed = time.time() - self._start_time
        self._emit("train.complete", {
            "total_steps": state.global_step,
            "final_loss": state.log_history[-1].get("loss") if state.log_history else None,
            "elapsed_seconds": elapsed,
            "output_dir": args.output_dir,
        })
