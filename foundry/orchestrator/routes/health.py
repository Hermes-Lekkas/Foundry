# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Health & System routes."""

from __future__ import annotations

from fastapi import APIRouter

from foundry import __version__
from foundry.config.hardware import detect_hardware

router = APIRouter()


@router.get("/")
async def api_root() -> dict:
    """API root - basic info and available endpoints."""
    from foundry import __version__
    return {
        "name": "The Foundry API",
        "version": __version__,
        "endpoints": [
            "/api/health",
            "/api/config/hardware",
            "/api/config/settings",
            "/api/config/tiers",
            "/api/data/synthesize",
            "/api/data/jobs",
            "/api/training/start",
            "/api/training/jobs",
            "/api/eval/run",
            "/api/eval/jobs",
        ],
    }


@router.get("/health")
async def health() -> dict:
    hw = detect_hardware()
    return {
        "status": "ok",
        "version": __version__,
        "gpu": hw.gpu.name,
        "vram_total_gb": round(hw.gpu.vram_total_gb, 1),
        "vram_free_gb": round(hw.gpu.vram_free_gb, 1),
        "cuda_available": hw.cuda_available,
        "platform": hw.platform.value,
        "is_wsl2": hw.is_wsl2,
        "tier": hw.tier.value,
        "dataset_num_proc": hw.dataset_num_proc,
    }
