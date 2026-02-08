# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""VRAM Management — Time-sharded model toggle and proactive profiler.

Two core responsibilities:
1. VRAMManager: Swap Teacher/Student models on the same GPU (time-sharding)
2. VRAMProfiler: Dry forward+backward pass to find max safe batch size
"""

from __future__ import annotations

import gc
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ModelRole(str, Enum):
    """Which model is currently loaded in VRAM."""

    NONE = "none"
    TEACHER = "teacher"
    STUDENT = "student"
    JUDGE = "judge"


@dataclass
class VRAMState:
    """Current VRAM state."""

    active_role: ModelRole = ModelRole.NONE
    model_name: str = ""
    vram_used_mb: int = 0
    vram_total_mb: int = 0
    vram_free_mb: int = 0

    @property
    def utilization(self) -> float:
        if self.vram_total_mb == 0:
            return 0.0
        return self.vram_used_mb / self.vram_total_mb


@dataclass
class ProfileResult:
    """Result of VRAM profiling dry pass."""

    model_name: str
    adapter_name: str
    max_batch_size: int
    safe_batch_size: int  # 90% ceiling
    vram_total_mb: int
    vram_peak_mb: int
    vram_ceiling_mb: int  # 90% of total
    seq_length: int
    profiled_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        return (
            f"[bold]Model:[/]          {self.model_name}\n"
            f"[bold]Adapter:[/]        {self.adapter_name or 'none'}\n"
            f"[bold]VRAM Total:[/]     {self.vram_total_mb} MB\n"
            f"[bold]VRAM Peak:[/]      {self.vram_peak_mb} MB\n"
            f"[bold]VRAM Ceiling:[/]   {self.vram_ceiling_mb} MB (90%)\n"
            f"[bold]Max Batch Size:[/] {self.max_batch_size}\n"
            f"[bold]Safe Batch Size:[/] {self.safe_batch_size}\n"
            f"[bold]Seq Length:[/]     {self.seq_length}"
        )


class VRAMManager:
    """Time-sharded VRAM manager — toggles models on a single GPU.

    The Foundry uses one GPU for multiple roles. VRAMManager ensures
    only one model occupies VRAM at a time, handling cleanup between swaps.
    """

    def __init__(self) -> None:
        self._state = VRAMState()
        self._loaded_model: Any = None
        self._loaded_tokenizer: Any = None

    @property
    def state(self) -> VRAMState:
        return self._state

    @property
    def model(self) -> Any:
        return self._loaded_model

    @property
    def tokenizer(self) -> Any:
        return self._loaded_tokenizer

    def _clear_vram(self) -> None:
        """Aggressively clear VRAM."""
        self._loaded_model = None
        self._loaded_tokenizer = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass
        self._state.active_role = ModelRole.NONE
        self._state.model_name = ""
        logger.info("VRAM cleared")

    def _update_vram_stats(self) -> None:
        """Refresh VRAM usage numbers."""
        try:
            import torch

            if torch.cuda.is_available():
                self._state.vram_used_mb = torch.cuda.memory_allocated() // (1024 * 1024)
                self._state.vram_total_mb = torch.cuda.get_device_properties(0).total_mem // (
                    1024 * 1024
                )
                self._state.vram_free_mb = self._state.vram_total_mb - self._state.vram_used_mb
        except ImportError:
            pass

    async def load(
        self,
        role: ModelRole,
        model_name: str,
        loader_kwargs: dict[str, Any] | None = None,
    ) -> tuple[Any, Any]:
        """Load a model into VRAM, clearing any existing model first.

        Returns (model, tokenizer) tuple.
        """
        if self._state.active_role == role and self._state.model_name == model_name:
            logger.info("Model %s already loaded as %s", model_name, role.value)
            return self._loaded_model, self._loaded_tokenizer

        logger.info("Swapping VRAM: %s -> %s (%s)", self._state.active_role.value, role.value, model_name)
        self._clear_vram()

        from foundry.shared.model_loader import load_model

        model, tokenizer = load_model(model_name, **(loader_kwargs or {}))

        self._loaded_model = model
        self._loaded_tokenizer = tokenizer
        self._state.active_role = role
        self._state.model_name = model_name
        self._update_vram_stats()

        logger.info(
            "Loaded %s as %s — VRAM: %d MB used / %d MB total",
            model_name,
            role.value,
            self._state.vram_used_mb,
            self._state.vram_total_mb,
        )
        return model, tokenizer

    async def unload(self) -> None:
        """Unload current model and free VRAM."""
        self._clear_vram()
        self._update_vram_stats()


class VRAMProfiler:
    """Proactive VRAM profiler — determines safe batch size before training.

    Runs a dry forward+backward pass with dummy data, using binary search
    to find the maximum batch size that fits in 90% of available VRAM.
    Results are cached per model+adapter combination.
    """

    CEILING_RATIO = 0.90
    CACHE_FILE = Path(".foundry_vram_cache.json")

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_path = (cache_dir or Path(".")) / self.CACHE_FILE.name
        self._cache: dict[str, ProfileResult] = {}
        self._load_cache()

    def _cache_key(self, model_name: str, adapter_name: str | None) -> str:
        raw = f"{model_name}:{adapter_name or 'none'}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _load_cache(self) -> None:
        if self._cache_path.exists():
            try:
                data = json.loads(self._cache_path.read_text())
                for key, val in data.items():
                    self._cache[key] = ProfileResult(**val)
            except Exception:
                logger.warning("Failed to load VRAM profile cache, starting fresh")

    def _save_cache(self) -> None:
        data = {}
        for key, result in self._cache.items():
            data[key] = {
                "model_name": result.model_name,
                "adapter_name": result.adapter_name,
                "max_batch_size": result.max_batch_size,
                "safe_batch_size": result.safe_batch_size,
                "vram_total_mb": result.vram_total_mb,
                "vram_peak_mb": result.vram_peak_mb,
                "vram_ceiling_mb": result.vram_ceiling_mb,
                "seq_length": result.seq_length,
                "profiled_at": result.profiled_at,
            }
        self._cache_path.write_text(json.dumps(data, indent=2))

    def get_cached(self, model_name: str, adapter_name: str | None = None) -> ProfileResult | None:
        key = self._cache_key(model_name, adapter_name)
        return self._cache.get(key)

    def profile(
        self,
        model_name: str,
        adapter_name: str | None = None,
        seq_length: int = 2048,
        max_search_batch: int = 64,
        force: bool = False,
    ) -> ProfileResult:
        """Profile VRAM usage for a model via dry forward+backward pass.

        Uses binary search to find the max batch size that stays under
        90% VRAM ceiling. Caches results for subsequent runs.
        """
        # Check cache first
        if not force:
            cached = self.get_cached(model_name, adapter_name)
            if cached is not None:
                logger.info("Using cached VRAM profile for %s", model_name)
                return cached

        try:
            import torch
        except ImportError:
            # CPU-only fallback
            return ProfileResult(
                model_name=model_name,
                adapter_name=adapter_name or "",
                max_batch_size=1,
                safe_batch_size=1,
                vram_total_mb=0,
                vram_peak_mb=0,
                vram_ceiling_mb=0,
                seq_length=seq_length,
            )

        if not torch.cuda.is_available():
            return ProfileResult(
                model_name=model_name,
                adapter_name=adapter_name or "",
                max_batch_size=1,
                safe_batch_size=1,
                vram_total_mb=0,
                vram_peak_mb=0,
                vram_ceiling_mb=0,
                seq_length=seq_length,
            )

        # Load model for profiling
        from foundry.shared.model_loader import load_model

        logger.info("Profiling VRAM for %s (seq_len=%d)...", model_name, seq_length)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        model, tokenizer = load_model(model_name, adapter_name=adapter_name)
        model.train()

        total_mb = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
        ceiling_mb = int(total_mb * self.CEILING_RATIO)

        # Binary search for max batch size
        low, high = 1, max_search_batch
        best_batch = 1
        peak_mb = 0

        while low <= high:
            mid = (low + high) // 2
            try:
                torch.cuda.reset_peak_memory_stats()
                dummy_input = torch.randint(
                    0, tokenizer.vocab_size, (mid, seq_length), device="cuda"
                )
                dummy_labels = dummy_input.clone()

                outputs = model(input_ids=dummy_input, labels=dummy_labels)
                outputs.loss.backward()
                model.zero_grad(set_to_none=True)

                current_peak = torch.cuda.max_memory_allocated() // (1024 * 1024)
                del dummy_input, dummy_labels, outputs
                torch.cuda.empty_cache()

                if current_peak <= ceiling_mb:
                    best_batch = mid
                    peak_mb = current_peak
                    low = mid + 1
                else:
                    high = mid - 1
            except RuntimeError:
                # OOM — reduce batch size
                high = mid - 1
                torch.cuda.empty_cache()
                gc.collect()

        # Cleanup
        del model, tokenizer
        gc.collect()
        torch.cuda.empty_cache()

        safe_batch = max(1, int(best_batch * self.CEILING_RATIO))

        result = ProfileResult(
            model_name=model_name,
            adapter_name=adapter_name or "",
            max_batch_size=best_batch,
            safe_batch_size=safe_batch,
            vram_total_mb=total_mb,
            vram_peak_mb=peak_mb,
            vram_ceiling_mb=ceiling_mb,
            seq_length=seq_length,
        )

        # Cache result
        key = self._cache_key(model_name, adapter_name)
        self._cache[key] = result
        self._save_cache()

        logger.info(
            "VRAM profile complete: max_batch=%d, safe_batch=%d, peak=%dMB/%dMB",
            best_batch,
            safe_batch,
            peak_mb,
            ceiling_mb,
        )
        return result
