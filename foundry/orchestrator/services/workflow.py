# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Workflow Orchestrator — Coordinates all 4 engines into a single pipeline.

Full pipeline: Configure -> Profile VRAM -> Synthesize Data -> Train -> Evaluate
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowPhase(str, Enum):
    CONFIGURE = "configure"
    PROFILE = "profile"
    SYNTHESIZE = "synthesize"
    TRAIN = "train"
    EVALUATE = "evaluate"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WorkflowConfig:
    """Configuration for a full training workflow."""

    # Model
    model_name: str = "unsloth/Qwen2.5-0.5B"

    # Data synthesis
    constitution: str = "agentic"
    pipeline: str = "trajectory"
    num_samples: int = 100
    teacher_model: str | None = None

    # Training
    trainer_type: str = "sft"
    num_epochs: int = 3
    learning_rate: float = 2e-4
    max_seq_length: int = 2048
    quantization: str = "4bit-nf4"
    lora_r: int = 16
    batch_size: int | None = None  # Auto from profiler

    # Evaluation
    benchmark: str = "all"

    # Output
    output_dir: str = "./checkpoints"


@dataclass
class WorkflowState:
    """Tracks the state of a workflow execution."""

    id: str = field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    phase: WorkflowPhase = WorkflowPhase.CONFIGURE
    config: WorkflowConfig = field(default_factory=WorkflowConfig)
    profile_result: dict[str, Any] | None = None
    synth_result: dict[str, Any] | None = None
    train_result: dict[str, Any] | None = None
    eval_result: dict[str, Any] | None = None
    error: str = ""

    @property
    def is_complete(self) -> bool:
        return self.phase in (WorkflowPhase.COMPLETE, WorkflowPhase.FAILED)


class WorkflowOrchestrator:
    """Orchestrates the full training pipeline across all engines."""

    def __init__(self) -> None:
        self._active_workflows: dict[str, WorkflowState] = {}

    async def run(
        self,
        config: WorkflowConfig,
        state_manager: Any = None,
        event_bus: Any = None,
    ) -> WorkflowState:
        """Execute the full pipeline: Profile -> Synthesize -> Train -> Evaluate."""
        workflow = WorkflowState(config=config)
        self._active_workflows[workflow.id] = workflow

        logger.info("Starting workflow %s", workflow.id)

        try:
            # Phase 1: VRAM Profile
            workflow.phase = WorkflowPhase.PROFILE
            if event_bus:
                await event_bus.emit(
                    "vram.profile.start",
                    {"workflow_id": workflow.id, "model": config.model_name},
                )

            from foundry.shared.vram import VRAMProfiler

            profiler = VRAMProfiler()
            profile = profiler.profile(
                model_name=config.model_name,
                seq_length=config.max_seq_length,
            )
            workflow.profile_result = {
                "safe_batch_size": profile.safe_batch_size,
                "max_batch_size": profile.max_batch_size,
                "vram_ceiling_mb": profile.vram_ceiling_mb,
            }

            batch_size = config.batch_size or profile.safe_batch_size
            logger.info("VRAM profile complete: using batch_size=%d", batch_size)

            # Phase 2: Data Synthesis
            workflow.phase = WorkflowPhase.SYNTHESIZE
            if event_bus:
                await event_bus.emit(
                    "data.synth.start",
                    {"workflow_id": workflow.id, "constitution": config.constitution},
                )

            from foundry.data_engine.pipelines.manager import run_synthesis

            constitution_path = self._resolve_constitution(config.constitution)
            dataset_path = await run_synthesis(
                constitution_path=constitution_path,
                num_samples=config.num_samples,
                pipeline_type=config.pipeline,
            )
            workflow.synth_result = {
                "dataset_path": str(dataset_path),
                "num_samples": config.num_samples,
            }
            logger.info("Data synthesis complete: %s", dataset_path)

            # Phase 3: Training
            workflow.phase = WorkflowPhase.TRAIN
            if event_bus:
                await event_bus.emit(
                    "train.start",
                    {"workflow_id": workflow.id, "model": config.model_name},
                )

            output_dir = f"{config.output_dir}/{workflow.id}"

            from foundry.training_core.run import _load_model_for_training, _load_dataset, _run_trainer

            model, tokenizer = _load_model_for_training(config.model_name, {
                "quantization": config.quantization,
                "lora_r": config.lora_r,
                "lora_alpha": config.lora_r,
                "max_seq_length": config.max_seq_length,
            })

            dataset = _load_dataset(str(dataset_path), config.trainer_type)

            train_result = _run_trainer(
                config.trainer_type, model, tokenizer, dataset,
                batch_size=batch_size,
                config={
                    "output_dir": output_dir,
                    "num_epochs": config.num_epochs,
                    "learning_rate": config.learning_rate,
                    "max_seq_length": config.max_seq_length,
                    "gradient_checkpointing": True,
                },
            )
            workflow.train_result = train_result
            logger.info("Training complete: %s", train_result)

            # Phase 4: Evaluation
            workflow.phase = WorkflowPhase.EVALUATE
            if event_bus:
                await event_bus.emit(
                    "eval.start",
                    {"workflow_id": workflow.id, "model": output_dir},
                )

            from foundry.evaluator.run import run_evaluation

            eval_result = await run_evaluation(
                model_path=Path(output_dir),
                benchmark=config.benchmark,
            )
            workflow.eval_result = eval_result
            logger.info("Evaluation complete: %s", eval_result)

            # Done
            workflow.phase = WorkflowPhase.COMPLETE
            logger.info("Workflow %s complete", workflow.id)

        except Exception as e:
            workflow.phase = WorkflowPhase.FAILED
            workflow.error = str(e)
            logger.exception("Workflow %s failed at phase %s", workflow.id, workflow.phase)
            if event_bus:
                await event_bus.emit(
                    "system.error",
                    {"workflow_id": workflow.id, "error": str(e)},
                )

        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowState | None:
        return self._active_workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowState]:
        return list(self._active_workflows.values())

    @staticmethod
    def _resolve_constitution(name: str) -> Path:
        from foundry.data_engine.pipelines.manager import _resolve_constitution
        return _resolve_constitution(name)
