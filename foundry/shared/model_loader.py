# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Unified ModelLoader — HuggingFace, Unsloth, and GGUF loading.

Provides a single entry point for loading models across all backends,
with automatic format detection and optimal configuration.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ModelFormat(str, Enum):
    """Supported model loading formats."""

    UNSLOTH = "unsloth"
    HUGGINGFACE = "huggingface"
    GGUF = "gguf"


def detect_format(model_name: str) -> ModelFormat:
    """Detect the appropriate loading format from the model name/path."""
    if model_name.endswith(".gguf"):
        return ModelFormat.GGUF
    if model_name.startswith("unsloth/") or "unsloth" in model_name.lower():
        return ModelFormat.UNSLOTH
    return ModelFormat.HUGGINGFACE


def load_model(
    model_name: str,
    adapter_name: str | None = None,
    quantization: str = "4bit",
    max_seq_length: int = 2048,
    dtype: str = "auto",
    format_override: ModelFormat | None = None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Load a model and tokenizer.

    Tries Unsloth first for optimized kernels, falls back to HuggingFace.
    Returns (model, tokenizer) tuple.
    """
    fmt = format_override or detect_format(model_name)

    if fmt == ModelFormat.UNSLOTH:
        return _load_unsloth(model_name, max_seq_length, quantization, adapter_name, **kwargs)
    elif fmt == ModelFormat.GGUF:
        return _load_gguf(model_name, **kwargs)
    else:
        return _load_huggingface(model_name, quantization, adapter_name, **kwargs)


def _load_unsloth(
    model_name: str,
    max_seq_length: int,
    quantization: str,
    adapter_name: str | None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Load via Unsloth for optimized 4-bit QLoRA training."""
    try:
        from unsloth import FastLanguageModel

        load_in_4bit = quantization in ("4bit", "4bit-nf4")

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            load_in_4bit=load_in_4bit,
            dtype=None,  # auto-detect
            **kwargs,
        )

        if adapter_name:
            # Apply LoRA adapter
            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=42,
            )

        logger.info("Loaded %s via Unsloth (4bit=%s)", model_name, load_in_4bit)
        return model, tokenizer

    except ImportError:
        logger.warning("Unsloth not available, falling back to HuggingFace")
        return _load_huggingface(model_name, quantization, adapter_name, **kwargs)


def _load_huggingface(
    model_name: str,
    quantization: str,
    adapter_name: str | None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """Load via HuggingFace Transformers with optional BitsAndBytes quantization."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs: dict[str, Any] = {"trust_remote_code": True, **kwargs}

    if quantization in ("4bit", "4bit-nf4"):
        try:
            from transformers import BitsAndBytesConfig

            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype="bfloat16",
                bnb_4bit_use_double_quant=True,
            )
        except ImportError:
            logger.warning("bitsandbytes not available, loading without quantization")

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    if adapter_name:
        try:
            from peft import LoraConfig, get_peft_model

            lora_config = LoraConfig(
                r=16,
                lora_alpha=16,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                lora_dropout=0.0,
                bias="none",
                task_type="CAUSAL_LM",
            )
            model = get_peft_model(model, lora_config)
        except ImportError:
            logger.warning("PEFT not available, skipping adapter")

    logger.info("Loaded %s via HuggingFace", model_name)
    return model, tokenizer


def _load_gguf(model_name: str, **kwargs: Any) -> tuple[Any, Any]:
    """Load a GGUF model (for inference only, not training)."""
    raise NotImplementedError(
        "GGUF loading is for inference/evaluation only. "
        "Use Unsloth or HuggingFace format for training."
    )
