# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Tests for configuration and hardware detection."""

from foundry.config.settings import FoundrySettings, get_settings
from foundry.config.hardware import (
    HardwareTier,
    PlatformType,
    TIER_CONFIGS,
    _classify_tier,
    _detect_platform,
    detect_hardware,
)


def test_settings_defaults():
    s = FoundrySettings()
    assert s.port == 8420
    assert s.host == "0.0.0.0"
    assert s.default_model == "unsloth/Qwen2.5-0.5B"
    assert s.sandbox_timeout == 30
    assert s.teacher_provider == "anthropic"


def test_settings_resolve_device():
    s = FoundrySettings(device="cpu")
    assert s.resolve_device() == "cpu"


def test_get_settings_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_tier_classification():
    assert _classify_tier(0) == HardwareTier.CPU_ONLY
    assert _classify_tier(7000) == HardwareTier.TIER_8GB
    assert _classify_tier(11000) == HardwareTier.TIER_12GB
    assert _classify_tier(24000) == HardwareTier.TIER_24GB
    assert _classify_tier(48000) == HardwareTier.TIER_48GB


def test_tier_configs_complete():
    for tier in HardwareTier:
        assert tier in TIER_CONFIGS
        config = TIER_CONFIGS[tier]
        assert "max_model_params" in config
        assert "recommended_models" in config
        assert "quantization" in config
        assert "batch_size_hint" in config


def test_detect_platform():
    plat, is_wsl2 = _detect_platform()
    assert isinstance(plat, PlatformType)
    assert isinstance(is_wsl2, bool)


def test_detect_hardware():
    hw = detect_hardware()
    assert hw.cpu_count >= 1
    assert hw.dataset_num_proc >= 1
    assert isinstance(hw.platform, PlatformType)
    assert isinstance(hw.tier, HardwareTier)
    assert isinstance(hw.recommendations, list)


def test_hardware_summary():
    hw = detect_hardware()
    summary = hw.summary()
    assert "Platform" in summary
    assert "GPU" in summary
    assert "Tier" in summary
