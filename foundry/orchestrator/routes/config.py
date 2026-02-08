# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Configuration routes — settings, hardware, tier recommendations."""

from __future__ import annotations

from fastapi import APIRouter

from foundry.config.hardware import TIER_CONFIGS, detect_hardware
from foundry.config.settings import get_settings

router = APIRouter()


@router.get("/hardware")
async def get_hardware():
    hw = detect_hardware()
    return {
        "platform": hw.platform.value,
        "gpu": {
            "name": hw.gpu.name,
            "vram_total_mb": hw.gpu.vram_total_mb,
            "vram_free_mb": hw.gpu.vram_free_mb,
            "cuda_version": hw.gpu.cuda_version,
            "driver_version": hw.gpu.driver_version,
        },
        "tier": hw.tier.value,
        "tier_config": hw.tier_config,
        "cpu_count": hw.cpu_count,
        "ram_total_gb": round(hw.ram_total_gb, 1),
        "dataset_num_proc": hw.dataset_num_proc,
        "recommendations": hw.recommendations,
    }


@router.get("/tiers")
async def get_tiers():
    return {tier.value: config for tier, config in TIER_CONFIGS.items()}


@router.get("/settings")
async def get_current_settings():
    s = get_settings()
    return {
        "device": s.resolve_device(),
        "default_model": s.default_model,
        "checkpoint_dir": str(s.checkpoint_dir),
        "dataset_dir": str(s.dataset_dir),
        "teacher_provider": s.teacher_provider,
        "teacher_model": s.teacher_model,
        "sandbox_timeout": s.sandbox_timeout,
        "sandbox_use_docker": s.sandbox_use_docker,
    }
