# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Pipeline Manager — Coordinates data synthesis across pipelines."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from foundry.data_engine.constitution import Constitution

logger = logging.getLogger(__name__)


def _create_teacher(provider: str | None = None, model: str | None = None) -> Any:
    """Create a teacher based on settings."""
    from foundry.config.settings import get_settings

    settings = get_settings()
    prov = provider or settings.teacher_provider
    mod = model or settings.teacher_model

    if prov in ("anthropic", "openai"):
        from foundry.data_engine.teachers.api_teacher import APITeacher

        return APITeacher(provider=prov, model=mod)
    else:
        from foundry.data_engine.teachers.local_teacher import LocalTeacher

        return LocalTeacher(model_name=mod)


async def run_synthesis(
    constitution_path: Path,
    num_samples: int = 100,
    output_dir: Path | None = None,
    pipeline_type: str = "trajectory",
    teacher_provider: str | None = None,
    teacher_model: str | None = None,
) -> Path:
    """Run data synthesis from CLI."""
    from foundry.config.settings import get_settings

    settings = get_settings()
    output_dir = output_dir or settings.dataset_dir / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    constitution = Constitution.from_yaml(constitution_path)
    teacher = _create_teacher(provider=teacher_provider, model=teacher_model)

    # Generate seed prompts
    prompts = await _generate_seed_prompts(teacher, constitution, num_samples)

    # Run pipeline
    if pipeline_type == "trajectory":
        from foundry.sandbox.tool_executor import ToolExecutor

        tool_executor = ToolExecutor()
        from foundry.data_engine.pipelines.trajectory import TrajectoryPipeline

        pipeline = TrajectoryPipeline(teacher, tool_executor, constitution)
        trajectories = await pipeline.process_batch(prompts)
        samples = [t.to_chat_format() for t in trajectories]
        tool_executor.cleanup()

    elif pipeline_type == "sl_cai":
        from foundry.data_engine.pipelines.sl_cai import SLCAIPipeline

        pipeline = SLCAIPipeline(teacher, constitution)  # type: ignore[assignment]
        sl_samples = await pipeline.process_batch(prompts)
        samples = [s.to_chat_format() for s in sl_samples]

    elif pipeline_type == "rl_cai":
        from foundry.data_engine.pipelines.rl_cai import RLCAIPipeline

        pipeline = RLCAIPipeline(teacher, constitution)  # type: ignore[assignment]
        pairs = await pipeline.process_batch(prompts)
        samples = [p.to_dpo_format() for p in pairs]

    else:
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")

    # Save output
    output_file = output_dir / f"{constitution.name}_{pipeline_type}_{uuid.uuid4().hex[:8]}.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    logger.info("Saved %d samples to %s", len(samples), output_file)
    return output_file


async def run_synthesis_job(
    job_id: str, req: Any, state: Any, bus: Any,
) -> None:
    """Run synthesis as a background job (called from API route)."""
    from foundry.shared.events import EventType

    try:
        await state.update_job(job_id, status="running")

        constitution_path = _resolve_constitution(req.constitution)
        constitution = Constitution.from_yaml(constitution_path)
        teacher = _create_teacher(model=req.teacher_model)

        prompts = await _generate_seed_prompts(teacher, constitution, req.num_samples)

        async def on_progress(current: int, total: int, *args: Any) -> None:
            await bus.emit(
                EventType.DATA_SYNTH_PROGRESS,
                {"job_id": job_id, "current": current, "total": total},
            )

        if req.pipeline == "trajectory":
            from foundry.sandbox.tool_executor import ToolExecutor

            tool_executor = ToolExecutor()
            from foundry.data_engine.pipelines.trajectory import TrajectoryPipeline

            pipeline = TrajectoryPipeline(teacher, tool_executor, constitution)
            trajectories = await pipeline.process_batch(prompts, on_progress)
            samples = [t.to_chat_format() for t in trajectories]
            tool_executor.cleanup()
        elif req.pipeline == "sl_cai":
            from foundry.data_engine.pipelines.sl_cai import SLCAIPipeline

            pipeline = SLCAIPipeline(teacher, constitution)  # type: ignore[assignment]
            sl_samples = await pipeline.process_batch(prompts, on_progress)
            samples = [s.to_chat_format() for s in sl_samples]
        elif req.pipeline == "rl_cai":
            from foundry.data_engine.pipelines.rl_cai import RLCAIPipeline

            pipeline = RLCAIPipeline(teacher, constitution)  # type: ignore[assignment]
            pairs = await pipeline.process_batch(prompts, on_progress)
            samples = [p.to_dpo_format() for p in pairs]
        else:
            raise ValueError(f"Unknown pipeline: {req.pipeline}")

        # Save
        from foundry.config.settings import get_settings

        output_dir = get_settings().dataset_dir / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{job_id}.jsonl"

        with open(output_file, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")

        # Register dataset
        dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
        await state.register_dataset(
            dataset_id, job_id, str(output_file),
            constitution=req.constitution, num_samples=len(samples),
        )

        await state.update_job(job_id, status="completed", result={
            "dataset_id": dataset_id,
            "num_samples": len(samples),
            "output_path": str(output_file),
        })
        await bus.emit(EventType.DATA_SYNTH_COMPLETE, {
            "job_id": job_id, "num_samples": len(samples),
        })

    except Exception as e:
        logger.exception("Synthesis job %s failed", job_id)
        await state.update_job(job_id, status="failed", error=str(e))
        await bus.emit(EventType.SYSTEM_ERROR, {"job_id": job_id, "error": str(e)})


async def _generate_seed_prompts(
    teacher: Any, constitution: Constitution, count: int,
) -> list[str]:
    """Use the teacher to generate seed task prompts for data synthesis."""
    from foundry.data_engine.teachers.base import Message

    domain_desc = constitution.description or constitution.name
    prompt = (
        f"Generate {count} diverse task prompts for training an AI assistant "
        f"in the domain of: {domain_desc}\n\n"
        f"Requirements:\n"
        f"- Each task should require using tools (file I/O, code execution, shell commands)\n"
        f"- Include tasks of varying difficulty (simple, moderate, complex)\n"
        f"- Include some tasks that will likely produce errors (to train error recovery)\n"
        f"- Format: one task per line, numbered 1-{count}\n"
        f"- Be specific and actionable\n"
    )

    response = await teacher.generate(
        [Message(role="user", content=prompt)],
        temperature=0.8,
        max_tokens=4096,
    )

    # Parse numbered list
    lines = response.content.strip().split("\n")
    prompts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Remove numbering
        for prefix in [".", ")", ":", "-"]:
            idx = line.find(prefix)
            if idx > 0 and idx < 5 and line[:idx].strip().isdigit():
                line = line[idx + 1:].strip()
                break
        if line:
            prompts.append(line)

    return prompts[:count]


def _resolve_constitution(name: str) -> Path:
    """Resolve a constitution name to a file path."""
    from foundry.config.settings import get_settings

    settings = get_settings()

    # Check if it's already a path
    p = Path(name)
    if p.exists():
        return p

    # Check constitutions directory
    const_path = settings.constitution_dir / f"{name}.yaml"
    if const_path.exists():
        return const_path

    raise FileNotFoundError(
        f"Constitution '{name}' not found. "
        f"Searched: {name}, {const_path}"
    )
