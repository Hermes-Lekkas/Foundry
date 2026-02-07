# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Health & System routes."""

from __future__ import annotations

from fastapi import APIRouter

from foundry import __version__
from foundry.config.hardware import detect_hardware

router = APIRouter()


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
