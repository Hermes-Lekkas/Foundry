# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""SFT Trainer — Supervised Fine-Tuning with TRL SFTTrainer.

Consumes constitutional-revised data from SL-CAI pipeline
or verified trajectories from the Trajectory pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SFTTrainerWrapper:
    """Wraps TRL SFTTrainer with Foundry integrations."""

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        dataset: Any,
        output_dir: str = "./checkpoints/sft",
        num_epochs: int = 3,
        batch_size: int = 4,
        gradient_accumulation_steps: int = 4,
        learning_rate: float = 2e-4,
        max_seq_length: int = 2048,
        warmup_ratio: float = 0.03,
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
        self.max_seq_length = max_seq_length
        self.warmup_ratio = warmup_ratio
        self.gradient_checkpointing = gradient_checkpointing
        self.dataset_num_proc = dataset_num_proc or self._auto_num_proc()

    @staticmethod
    def _auto_num_proc() -> int:
        from foundry.config.hardware import detect_hardware
        return detect_hardware().dataset_num_proc

    def build(self) -> Any:
        """Build and return the TRL SFTTrainer."""
        from trl import SFTTrainer, SFTConfig

        config = SFTConfig(
            output_dir=self.output_dir,
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.gradient_accumulation_steps,
            learning_rate=self.learning_rate,
            max_seq_length=self.max_seq_length,
            warmup_ratio=self.warmup_ratio,
            gradient_checkpointing=self.gradient_checkpointing,
            logging_steps=10,
            save_steps=500,
            save_total_limit=3,
            fp16=False,
            bf16=True,
            optim="adamw_8bit",
            lr_scheduler_type="cosine",
            seed=42,
            dataset_num_proc=self.dataset_num_proc,
            packing=True,
            report_to="none",
        )

        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=self.dataset,
            args=config,
        )

        logger.info(
            "SFT Trainer built: epochs=%d, batch=%d, lr=%e, seq_len=%d",
            self.num_epochs, self.batch_size, self.learning_rate, self.max_seq_length,
        )
        return trainer

    def train(self, resume_from: str | None = None) -> dict[str, Any]:
        """Build trainer and run training."""
        trainer = self.build()

        # Add Foundry telemetry callback
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
