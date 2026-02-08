# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""DPO Trainer — Direct Preference Optimization with TRL DPOTrainer.

Consumes preference pairs from the RL-CAI pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DPOTrainerWrapper:
    """Wraps TRL DPOTrainer with Foundry integrations."""

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        dataset: Any,
        output_dir: str = "./checkpoints/dpo",
        num_epochs: int = 1,
        batch_size: int = 2,
        gradient_accumulation_steps: int = 8,
        learning_rate: float = 5e-5,
        max_length: int = 2048,
        max_prompt_length: int = 512,
        beta: float = 0.1,
        gradient_checkpointing: bool = True,
        dataset_num_proc: int | None = None,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.dataset = dataset
        self.output_dir = output_dir
        self.num_epochs = num_epochs
        self.batch_size = batch_size
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.learning_rate = learning_rate
        self.max_length = max_length
        self.max_prompt_length = max_prompt_length
        self.beta = beta
        self.gradient_checkpointing = gradient_checkpointing
        self.dataset_num_proc = dataset_num_proc or self._auto_num_proc()

    @staticmethod
    def _auto_num_proc() -> int:
        from foundry.config.hardware import detect_hardware
        return detect_hardware().dataset_num_proc

    def build(self) -> Any:
        """Build and return the TRL DPOTrainer."""
        from trl import DPOTrainer, DPOConfig

        config = DPOConfig(
            output_dir=self.output_dir,
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            max_length=self.max_length,
            max_prompt_length=self.max_prompt_length,
            beta=self.beta,
            gradient_checkpointing=self.gradient_checkpointing,
            logging_steps=10,
            save_steps=500,
            save_total_limit=3,
            bf16=True,
            optim="adamw_8bit",
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            seed=42,
            report_to="none",
        )

        trainer = DPOTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=self.dataset,
            args=config,
        )

        logger.info(
            "DPO Trainer built: epochs=%d, batch=%d, beta=%.2f",
            self.num_epochs, self.batch_size, self.beta,
        )
        return trainer

    def train(self, resume_from: str | None = None) -> dict[str, Any]:
        """Build trainer and run training."""
        trainer = self.build()

        from foundry.training_core.telemetry.callback import FoundryCallback
        trainer.add_callback(FoundryCallback())

        result = trainer.train(resume_from_checkpoint=resume_from)
        trainer.save_model(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)

        return {
            "train_loss": result.training_loss,
            "train_steps": result.global_step,
            "output_dir": self.output_dir,
        }
