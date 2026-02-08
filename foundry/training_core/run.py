# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Training Run — Entry point for training jobs from CLI and API."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


async def run_training(config_path: Path, model_override: str | None = None) -> dict[str, Any]:
    """Run a training job from a YAML config file (CLI entry point)."""
    config = yaml.safe_load(config_path.read_text())

    model_name = model_override or config["model_name"]
    trainer_type = config.get("trainer_type", "sft")
    dataset_path = config.get("dataset_path")

    # VRAM profiling
    from foundry.shared.vram import VRAMProfiler

    profiler = VRAMProfiler()
    profile = profiler.profile(model_name)
    batch_size = config.get("batch_size") or profile.safe_batch_size

    logger.info(
        "VRAM profile: safe_batch=%d, using batch=%d",
        profile.safe_batch_size, batch_size,
    )

    # Load model
    model, tokenizer = _load_model_for_training(model_name, config)

    # Load dataset
    dataset = _load_dataset(dataset_path, trainer_type)

    # Create and run trainer
    result = _run_trainer(
        trainer_type, model, tokenizer, dataset,
        batch_size=batch_size, config=config,
    )

    return result


async def run_training_job(
    job_id: str, req: Any, state: Any, bus: Any,
) -> None:
    """Run training as a background job (called from API route)."""
    from foundry.shared.events import EventType

    try:
        await state.update_job(job_id, status="running")

        # VRAM profiling
        from foundry.shared.vram import VRAMProfiler

        profiler = VRAMProfiler()
        profile = profiler.profile(req.model_name)
        batch_size = req.batch_size or profile.safe_batch_size

        await bus.emit(EventType.VRAM_PROFILE_COMPLETE, {
            "job_id": job_id,
            "safe_batch_size": profile.safe_batch_size,
            "using_batch_size": batch_size,
            "vram_ceiling_mb": profile.vram_ceiling_mb,
        })

        # Load model
        model, tokenizer = _load_model_for_training(req.model_name, {
            "quantization": req.quantization,
            "lora_r": req.lora_r,
            "lora_alpha": req.lora_alpha,
            "max_seq_length": req.max_seq_length,
        })

        # Load dataset
        dataset_path = req.dataset_path
        if not dataset_path and req.dataset_id:
            job_data = await state.get_job(req.dataset_id)
            if job_data and job_data.get("result"):
                result_data = json.loads(job_data["result"]) if isinstance(job_data["result"], str) else job_data["result"]
                dataset_path = result_data.get("output_path")

        dataset = _load_dataset(dataset_path, req.trainer_type)

        # Train
        output_dir = f"./checkpoints/{job_id}"
        result = _run_trainer(
            req.trainer_type, model, tokenizer, dataset,
            batch_size=batch_size,
            config={
                "output_dir": output_dir,
                "num_epochs": req.num_epochs,
                "learning_rate": req.learning_rate,
                "max_seq_length": req.max_seq_length,
                "gradient_accumulation_steps": req.gradient_accumulation_steps,
                "gradient_checkpointing": req.gradient_checkpointing,
                "warmup_ratio": req.warmup_ratio,
            },
        )

        await state.update_job(job_id, status="completed", result=result)
        await bus.emit(EventType.TRAIN_COMPLETE, {"job_id": job_id, **result})

    except Exception as e:
        logger.exception("Training job %s failed", job_id)
        await state.update_job(job_id, status="failed", error=str(e))
        await bus.emit(EventType.SYSTEM_ERROR, {"job_id": job_id, "error": str(e)})


def _load_model_for_training(model_name: str, config: dict[str, Any]) -> tuple[Any, Any]:
    """Load model using the best available backend."""
    from foundry.training_core.backends.unsloth_backend import UnslothBackend
    from foundry.training_core.backends.native_backend import NativeBackend

    if UnslothBackend.is_available():
        return UnslothBackend.load_model(
            model_name,
            max_seq_length=config.get("max_seq_length", 2048),
            load_in_4bit=config.get("quantization", "4bit") in ("4bit", "4bit-nf4"),
            lora_r=config.get("lora_r", 16),
            lora_alpha=config.get("lora_alpha", 16),
        )
    else:
        return NativeBackend.load_model(
            model_name,
            quantization=config.get("quantization", "4bit-nf4"),
            lora_r=config.get("lora_r", 16),
            lora_alpha=config.get("lora_alpha", 16),
        )


def _load_dataset(dataset_path: str | None, trainer_type: str) -> Any:
    """Load dataset from path."""
    if not dataset_path:
        raise ValueError("No dataset path provided")

    from datasets import load_dataset

    if dataset_path.endswith(".jsonl"):
        ds = load_dataset("json", data_files=dataset_path, split="train")
    elif dataset_path.endswith(".parquet"):
        ds = load_dataset("parquet", data_files=dataset_path, split="train")
    else:
        ds = load_dataset(dataset_path, split="train")

    logger.info("Loaded dataset: %d samples from %s", len(ds), dataset_path)
    return ds


def _run_trainer(
    trainer_type: str,
    model: Any,
    tokenizer: Any,
    dataset: Any,
    batch_size: int = 4,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Instantiate and run the appropriate trainer."""
    config = config or {}

    if trainer_type == "sft":
        from foundry.training_core.trainers.sft import SFTTrainerWrapper

        wrapper = SFTTrainerWrapper(
            model=model,
            tokenizer=tokenizer,
            dataset=dataset,
            output_dir=config.get("output_dir", "./checkpoints/sft"),
            num_epochs=config.get("num_epochs", 3),
            batch_size=batch_size,
            gradient_accumulation_steps=config.get("gradient_accumulation_steps", 4),
            learning_rate=config.get("learning_rate", 2e-4),
            max_seq_length=config.get("max_seq_length", 2048),
            warmup_ratio=config.get("warmup_ratio", 0.03),
            gradient_checkpointing=config.get("gradient_checkpointing", True),
        )
        return wrapper.train()

    elif trainer_type == "dpo":
        from foundry.training_core.trainers.dpo import DPOTrainerWrapper

        wrapper = DPOTrainerWrapper(
            model=model,
            tokenizer=tokenizer,
            dataset=dataset,
            output_dir=config.get("output_dir", "./checkpoints/dpo"),
            num_epochs=config.get("num_epochs", 1),
            batch_size=batch_size,
            gradient_accumulation_steps=config.get("gradient_accumulation_steps", 8),
            learning_rate=config.get("learning_rate", 5e-5),
            gradient_checkpointing=config.get("gradient_checkpointing", True),
        )
        return wrapper.train()

    elif trainer_type == "grpo":
        from foundry.training_core.trainers.grpo import GRPOTrainerWrapper
        from foundry.evaluator.rewards.functions import get_default_reward_funcs

        reward_funcs = get_default_reward_funcs()
        wrapper = GRPOTrainerWrapper(
            model=model,
            tokenizer=tokenizer,
            dataset=dataset,
            reward_funcs=reward_funcs,
            output_dir=config.get("output_dir", "./checkpoints/grpo"),
            num_epochs=config.get("num_epochs", 1),
            batch_size=batch_size,
            gradient_accumulation_steps=config.get("gradient_accumulation_steps", 8),
            learning_rate=config.get("learning_rate", 5e-6),
            gradient_checkpointing=config.get("gradient_checkpointing", True),
        )
        return wrapper.train()

    else:
        raise ValueError(f"Unknown trainer type: {trainer_type}")
