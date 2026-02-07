# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Training routes — start/stop training, checkpoints, telemetry."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class TrainingRequest(BaseModel):
    model_name: str
    dataset_id: str | None = None
    dataset_path: str | None = None
    trainer_type: str = "sft"  # sft | dpo | grpo
    optimizer: str = "muon_adamw"
    quantization: str = "4bit-nf4"
    lora_r: int = 16
    lora_alpha: int = 16
    learning_rate: float = 2e-4
    num_epochs: int = 3
    max_seq_length: int = 2048
    batch_size: int | None = None  # None = use VRAM profiler
    gradient_accumulation_steps: int = 4
    gradient_checkpointing: bool = True
    warmup_ratio: float = 0.03


@router.post("/start")
async def start_training(req: TrainingRequest, request: Request):
    """Start a training job."""
    from foundry.shared.events import EventType, get_event_bus

    job_id = f"train_{uuid.uuid4().hex[:8]}"
    state = request.app.state.state_manager
    bus = get_event_bus()

    await state.create_job(job_id, "training", req.model_dump())
    await bus.emit(EventType.TRAIN_START, {"job_id": job_id, **req.model_dump()})

    import asyncio

    from foundry.training_core.run import run_training_job

    asyncio.create_task(run_training_job(job_id, req, state, bus))

    return {"job_id": job_id, "status": "started"}


@router.get("/jobs")
async def list_training_jobs(request: Request):
    state = request.app.state.state_manager
    return await state.list_jobs(job_type="training")


@router.get("/jobs/{job_id}")
async def get_training_job(job_id: str, request: Request):
    state = request.app.state.state_manager
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/stop")
async def stop_training(job_id: str, request: Request):
    """Request training job cancellation."""
    state = request.app.state.state_manager
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await state.update_job(job_id, status="cancelling")
    return {"job_id": job_id, "status": "cancelling"}


@router.post("/profile")
async def profile_vram(model_name: str, adapter_name: str | None = None):
    """Run VRAM profiler for a model."""
    from foundry.shared.vram import VRAMProfiler

    profiler = VRAMProfiler()
    result = profiler.profile(model_name=model_name, adapter_name=adapter_name)
    return {
        "model_name": result.model_name,
        "max_batch_size": result.max_batch_size,
        "safe_batch_size": result.safe_batch_size,
        "vram_total_mb": result.vram_total_mb,
        "vram_peak_mb": result.vram_peak_mb,
        "vram_ceiling_mb": result.vram_ceiling_mb,
    }
