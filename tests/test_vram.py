# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for VRAM management."""

import pytest
from foundry.shared.vram import (
    VRAMManager,
    VRAMProfiler,
    VRAMState,
    ModelRole,
    ProfileResult,
)


def test_vram_state_defaults():
    state = VRAMState()
    assert state.active_role == ModelRole.NONE
    assert state.utilization == 0.0


def test_vram_state_utilization():
    state = VRAMState(vram_used_mb=12000, vram_total_mb=24000)
    assert state.utilization == 0.5


def test_profile_result_summary():
    result = ProfileResult(
        model_name="test-model",
        adapter_name="",
        max_batch_size=8,
        safe_batch_size=7,
        vram_total_mb=24000,
        vram_peak_mb=20000,
        vram_ceiling_mb=21600,
        seq_length=2048,
    )
    summary = result.summary()
    assert "test-model" in summary
    assert "8" in summary  # max batch
    assert "7" in summary  # safe batch


def test_vram_manager_initial_state():
    manager = VRAMManager()
    assert manager.state.active_role == ModelRole.NONE
    assert manager.model is None
    assert manager.tokenizer is None


def test_profiler_cache_key():
    profiler = VRAMProfiler()
    key1 = profiler._cache_key("model-a", None)
    key2 = profiler._cache_key("model-a", "lora16")
    key3 = profiler._cache_key("model-a", None)
    assert key1 != key2
    assert key1 == key3


def test_profiler_cpu_fallback():
    """On CPU-only systems, profiler should return safe defaults."""
    profiler = VRAMProfiler()
    result = profiler.profile("nonexistent-model")
    assert result.safe_batch_size >= 1
    assert result.max_batch_size >= 1


def test_model_role_enum():
    assert ModelRole.TEACHER.value == "teacher"
    assert ModelRole.STUDENT.value == "student"
    assert ModelRole.JUDGE.value == "judge"
