# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Evaluation routes — run benchmarks, view results, leaderboard."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class EvalRequest(BaseModel):
    model_path: str
    benchmark: str = "all"  # all | humaneval | gsm8k | custom
    judge_type: str = "prometheus"  # prometheus | llm | rule
    judge_model: str | None = None
    num_samples: int | None = None


@router.post("/run")
async def start_eval(req: EvalRequest, request: Request):
    """Start an evaluation job."""
    from foundry.shared.events import EventType, get_event_bus

    job_id = f"eval_{uuid.uuid4().hex[:8]}"
    state = request.app.state.state_manager
    bus = get_event_bus()

    await state.create_job(job_id, "evaluation", req.model_dump())
    await bus.emit(EventType.EVAL_START, {"job_id": job_id, **req.model_dump()})

    import asyncio

    from foundry.evaluator.run import run_eval_job

    asyncio.create_task(run_eval_job(job_id, req, state, bus))

    return {"job_id": job_id, "status": "started"}


@router.get("/jobs")
async def list_eval_jobs(request: Request):
    state = request.app.state.state_manager
    return await state.list_jobs(job_type="evaluation")


@router.get("/jobs/{job_id}")
async def get_eval_job(job_id: str, request: Request):
    state = request.app.state.state_manager
    job = await state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/results")
async def list_results(request: Request):
    state = request.app.state.state_manager
    return await state.list_eval_results()


@router.get("/leaderboard")
async def leaderboard(request: Request):
    """Return a model leaderboard sorted by aggregate scores."""
    state = request.app.state.state_manager
    results = await state.list_eval_results(limit=100)

    import json

    board: dict[str, dict[str, Any]] = {}
    for r in results:
        model = r["model_path"]
        scores = json.loads(r.get("scores", "{}"))
        if model not in board:
            board[model] = {"model": model, "benchmarks": {}, "avg_score": 0.0}
        board[model]["benchmarks"][r["benchmark"]] = scores

    # Calculate average scores
    for entry in board.values():
        all_scores = []
        for bm_scores in entry["benchmarks"].values():
            if isinstance(bm_scores, dict) and "score" in bm_scores:
                all_scores.append(bm_scores["score"])
        entry["avg_score"] = sum(all_scores) / len(all_scores) if all_scores else 0.0

    return sorted(board.values(), key=lambda x: x["avg_score"], reverse=True)
