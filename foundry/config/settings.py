# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Foundry Settings — Pydantic Settings with .env and auto-detection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FoundrySettings(BaseSettings):
    """Central configuration for The Foundry."""

    model_config = SettingsConfigDict(
        env_prefix="FOUNDRY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8420
    log_level: str = "info"

    # ── API Keys ──────────────────────────────────────────────────────────────
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # ── Hardware overrides ────────────────────────────────────────────────────
    device: str = "auto"
    vram_limit_gb: Optional[float] = None

    # ── Paths ─────────────────────────────────────────────────────────────────
    checkpoint_dir: Path = Path("./checkpoints")
    dataset_dir: Path = Path("./datasets")
    constitution_dir: Path = Path("./constitutions")

    # ── Training defaults ─────────────────────────────────────────────────────
    default_model: str = "unsloth/Qwen2.5-0.5B"

    # ── Sandbox ───────────────────────────────────────────────────────────────
    sandbox_timeout: int = 30
    sandbox_use_docker: bool = False

    # ── Teacher ───────────────────────────────────────────────────────────────
    teacher_provider: str = "anthropic"
    teacher_model: str = "claude-sonnet-4-5-20250929"

    def resolve_device(self) -> str:
        """Resolve 'auto' device to actual device string."""
        if self.device != "auto":
            return self.device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"


@lru_cache(maxsize=1)
def get_settings() -> FoundrySettings:
    """Get cached settings instance."""
    return FoundrySettings()
