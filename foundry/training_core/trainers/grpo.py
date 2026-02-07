# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""GRPO Trainer — Group Relative Policy Optimization with composable rewards.

GRPO combines:
- Hard reward: Sandbox executes generated code -> binary 0/1
- Soft reward: Constitutional judge scores reasoning quality -> 0.0-1.0
- Combined: r = alpha * hard + (1-alpha) * soft
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Type for reward functions: takes (prompts, completions, **kwargs) -> list[float]
RewardFunction = Callable[..., list[float]]


class GRPOTrainerWrapper:
    """Wraps TRL GRPOTrainer with sandbox-backed reward functions.

    GRPO uses group-relative scoring: for each prompt, generate a group
    of completions, compute rewards, normalize within the group, and
    use the relative ranking for policy gradient updates.
    """

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        dataset: Any,
        reward_funcs: list[RewardFunction] | None = None,
        reward_weights: list[float] | None = None,
        output_dir: str = "./checkpoints/grpo",
        num_epochs: int = 1,
        batch_size: int = 2,
        gradient_accumulation_steps: int = 8,
        learning_rate: float = 5e-6,
        max_length: int = 2048,
        num_generations: int = 4,
        gradient_checkpointing: bool = True,
        dataset_num_proc: int | None = None,
    ) -> None:
        self.model = model
        self.tokenizer = tokenizer
        self.dataset = dataset
        self.reward_funcs = reward_funcs or []
        self.reward_weights = reward_weights or [1.0] * len(self.reward_funcs)
        self.output_dir = output_dir
        self.num_epochs = num_epochs
        self.batch_size = batch_size
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.learning_rate = learning_rate
        self.max_length = max_length
        self.num_generations = num_generations
        self.gradient_checkpointing = gradient_checkpointing
        self.dataset_num_proc = dataset_num_proc or self._auto_num_proc()

    @staticmethod
    def _auto_num_proc() -> int:
        from foundry.config.hardware import detect_hardware
        return detect_hardware().dataset_num_proc

    def build(self) -> Any:
        """Build and return the TRL GRPOTrainer."""
        from trl import GRPOTrainer, GRPOConfig

        config = GRPOConfig(
            output_dir=self.output_dir,
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            max_completion_length=self.max_length,
            num_generations=self.num_generations,
            gradient_checkpointing=self.gradient_checkpointing,
            logging_steps=1,
            save_steps=200,
            save_total_limit=3,
            bf16=True,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            seed=42,
            report_to="none",
        )

        trainer = GRPOTrainer(
            model=self.model,
            processing_class=self.tokenizer,
            train_dataset=self.dataset,
            reward_funcs=self.reward_funcs,
            args=config,
        )

        logger.info(
            "GRPO Trainer built: epochs=%d, batch=%d, generations=%d, rewards=%d",
            self.num_epochs, self.batch_size, self.num_generations, len(self.reward_funcs),
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
