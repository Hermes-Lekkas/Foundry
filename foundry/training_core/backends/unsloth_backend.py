# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Unsloth Backend — Optimized 4-bit QLoRA training with fused kernels."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class UnslothBackend:
    """Training backend using Unsloth for optimized kernel execution.

    Unsloth provides:
    - 2x faster training via fused attention kernels
    - 60% less VRAM via optimized gradient checkpointing
    - Native 4-bit QLoRA with NF4 quantization
    """

    name = "unsloth"

    @staticmethod
    def is_available() -> bool:
        try:
            import unsloth
            return True
        except ImportError:
            return False

    @staticmethod
    def load_model(
        model_name: str,
        max_seq_length: int = 2048,
        load_in_4bit: bool = True,
        lora_r: int = 16,
        lora_alpha: int = 16,
        target_modules: list[str] | None = None,
    ) -> tuple[Any, Any]:
        """Load model with Unsloth optimizations and LoRA."""
        from unsloth import FastLanguageModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            load_in_4bit=load_in_4bit,
            dtype=None,
        )

        targets = target_modules or [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]

        model = FastLanguageModel.get_peft_model(
            model,
            r=lora_r,
            target_modules=targets,
            lora_alpha=lora_alpha,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=42,
        )

        logger.info(
            "Loaded %s via Unsloth (4bit=%s, r=%d, targets=%s)",
            model_name, load_in_4bit, lora_r, targets,
        )
        return model, tokenizer

    @staticmethod
    def prepare_for_inference(model: Any) -> Any:
        """Switch model to inference mode (2x faster generation)."""
        from unsloth import FastLanguageModel

        FastLanguageModel.for_inference(model)
        return model

    @staticmethod
    def save_model(
        model: Any,
        tokenizer: Any,
        output_dir: str,
        save_method: str = "lora",
    ) -> None:
        """Save model — lora adapters, merged 16bit, or quantized."""
        if save_method == "lora":
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)
        elif save_method == "merged_16bit":
            model.save_pretrained_merged(output_dir, tokenizer, save_method="merged_16bit")
        elif save_method == "gguf":
            model.save_pretrained_gguf(output_dir, tokenizer, quantization_method="q4_k_m")
        else:
            raise ValueError(f"Unknown save method: {save_method}")
        logger.info("Saved model to %s (method=%s)", output_dir, save_method)
