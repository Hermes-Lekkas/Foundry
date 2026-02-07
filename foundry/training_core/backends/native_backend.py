# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Native PyTorch Backend — Raw training loop for maximum control."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NativeBackend:
    """Training backend using vanilla PyTorch + HuggingFace Transformers.

    Fallback when Unsloth is unavailable. Provides full control
    over the training loop at the cost of less optimization.
    """

    name = "native"

    @staticmethod
    def is_available() -> bool:
        try:
            import torch
            import transformers
            return True
        except ImportError:
            return False

    @staticmethod
    def load_model(
        model_name: str,
        quantization: str = "4bit-nf4",
        lora_r: int = 16,
        lora_alpha: int = 16,
        target_modules: list[str] | None = None,
    ) -> tuple[Any, Any]:
        """Load model with HuggingFace + optional BnB quantization + PEFT."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model_kwargs: dict[str, Any] = {"trust_remote_code": True}

        if quantization in ("4bit", "4bit-nf4"):
            from transformers import BitsAndBytesConfig
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype="bfloat16",
                bnb_4bit_use_double_quant=True,
            )

        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

        # Apply LoRA
        from peft import LoraConfig, get_peft_model

        targets = target_modules or [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]
        lora_config = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            target_modules=targets,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        logger.info("Loaded %s via Native backend (quant=%s)", model_name, quantization)
        return model, tokenizer

    @staticmethod
    def save_model(model: Any, tokenizer: Any, output_dir: str) -> None:
        """Save model and tokenizer."""
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        logger.info("Saved model to %s", output_dir)
