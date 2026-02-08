# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Data Engine routes — synthesis, datasets, constitutions."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class SynthesisRequest(BaseModel):
    constitution: str = "agentic"
    pipeline: str = "trajectory"  # trajectory | sl_cai | rl_cai
    num_samples: int = 100
    teacher_model: str | None = None


class ConstitutionUpload(BaseModel):
    name: str
    content: str  # YAML content


@router.post("/synthesize")
async def start_synthesis(req: SynthesisRequest, request: Request):
    """Start a data synthesis job."""
    from foundry.shared.events import EventType, get_event_bus

    job_id = f"synth_{uuid.uuid4().hex[:8]}"
    state = request.app.state.state_manager
    bus = get_event_bus()

    await state.create_job(job_id, "synthesis", req.model_dump())
    await bus.emit(EventType.DATA_SYNTH_START, {"job_id": job_id, **req.model_dump()})

    # Launch synthesis in background
    import asyncio

    from foundry.data_engine.pipelines.manager import run_synthesis_job

    asyncio.create_task(run_synthesis_job(job_id, req, state, bus))

    return {"job_id": job_id, "status": "started"}


@router.get("/jobs")
async def list_data_jobs(request: Request):
    state = request.app.state.state_manager
    return await state.list_jobs(job_type="synthesis")


@router.get("/jobs/{job_id}")
async def get_data_job(job_id: str, request: Request):
    state = request.app.state.state_manager
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/datasets")
async def list_datasets(request: Request):
    state = request.app.state.state_manager
    return await state.list_datasets()


@router.get("/constitutions")
async def list_constitutions():
    """List available constitution files."""
    from foundry.config.settings import get_settings

    settings = get_settings()
    const_dir = settings.constitution_dir
    if not const_dir.exists():
        return []
    return [
        {"name": f.stem, "path": str(f)}
        for f in sorted(const_dir.glob("*.yaml"))
    ]
