# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Evaluation Run — Entry point for evaluation jobs from CLI and API."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def run_evaluation(
    model_path: Path, benchmark: str = "all",
) -> dict[str, Any]:
    """Run evaluation from CLI."""
    from foundry.shared.model_loader import load_model

    model, tokenizer = load_model(str(model_path))

    from foundry.evaluator.benchmarks.runner import BenchmarkRunner

    runner = BenchmarkRunner(model, tokenizer)
    results = await runner.run(benchmark)

    output = {
        "model": str(model_path),
        "benchmarks": {r.benchmark: {"score": r.score, "correct": r.correct, "total": r.total} for r in results},
    }

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Evaluation Results")
    table.add_column("Benchmark")
    table.add_column("Score", justify="right")
    table.add_column("Correct/Total", justify="right")

    for r in results:
        table.add_row(r.benchmark, f"{r.score * 100:.1f}%", f"{r.correct}/{r.total}")

    console.print(table)
    return output


async def run_eval_job(
    job_id: str, req: Any, state: Any, bus: Any,
) -> None:
    """Run evaluation as a background job (called from API route)."""
    from foundry.shared.events import EventType

    try:
        await state.update_job(job_id, status="running")

        from foundry.shared.model_loader import load_model

        model, tokenizer = load_model(req.model_path)

        from foundry.evaluator.benchmarks.runner import BenchmarkRunner

        runner = BenchmarkRunner(model, tokenizer)
        results = await runner.run(req.benchmark)

        # Save results
        for r in results:
            eval_id = f"eval_{uuid.uuid4().hex[:8]}"
            await state.save_eval_result(
                eval_id, req.model_path, r.benchmark,
                {"score": r.score, "correct": r.correct, "total": r.total},
            )

        output = {
            "benchmarks": {
                r.benchmark: {"score": r.score, "correct": r.correct, "total": r.total}
                for r in results
            },
        }

        await state.update_job(job_id, status="completed", result=output)
        await bus.emit(EventType.EVAL_COMPLETE, {"job_id": job_id, **output})

    except Exception as e:
        logger.exception("Eval job %s failed", job_id)
        await state.update_job(job_id, status="failed", error=str(e))
        await bus.emit(EventType.SYSTEM_ERROR, {"job_id": job_id, "error": str(e)})
