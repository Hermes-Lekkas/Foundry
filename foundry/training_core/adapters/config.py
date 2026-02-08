# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Adapter Configuration — QLoRA 4-bit NF4 and standard LoRA configs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


@dataclass
class AdapterConfig:
    """Configuration for LoRA/QLoRA adapters."""

    r: int = 16
    lora_alpha: int = 16
    target_modules: list[str] = field(default_factory=lambda: DEFAULT_TARGET_MODULES.copy())
    lora_dropout: float = 0.0
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    quantization: str = "4bit-nf4"
    use_gradient_checkpointing: bool = True

    def to_peft_config(self) -> Any:
        """Convert to PEFT LoraConfig."""
        from peft import LoraConfig

        return LoraConfig(
            r=self.r,
            lora_alpha=self.lora_alpha,
            target_modules=self.target_modules,
            lora_dropout=self.lora_dropout,
            bias=self.bias,
            task_type=self.task_type,
        )


def create_adapter_config(
    tier: str = "24gb",
    task: str = "sft",
) -> AdapterConfig:
    """Create an adapter config based on hardware tier and task."""
    if tier in ("8gb", "12gb"):
        return AdapterConfig(r=8, lora_alpha=8, quantization="4bit-nf4")
    elif tier == "24gb":
        return AdapterConfig(r=16, lora_alpha=16, quantization="4bit-nf4")
    else:
        return AdapterConfig(r=32, lora_alpha=32, quantization="4bit-nf4")


def merge_adapter(model: Any, output_dir: str) -> None:
    """Merge LoRA adapter into base model for deployment."""
    merged = model.merge_and_unload()
    merged.save_pretrained(output_dir)
    logger.info("Merged adapter into %s", output_dir)
