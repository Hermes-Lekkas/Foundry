# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""SQLite State Manager — Persistent state for jobs, runs, and datasets."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = ".foundry_state.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    config TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    constitution TEXT,
    num_samples INTEGER DEFAULT 0,
    format TEXT DEFAULT 'jsonl',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    path TEXT NOT NULL,
    step INTEGER,
    metrics TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS eval_results (
    id TEXT PRIMARY KEY,
    model_path TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    scores TEXT,
    created_at TEXT NOT NULL
);
"""


class StateManager:
    """Async SQLite state manager for The Foundry."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info("State manager initialized: %s", self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Jobs ──────────────────────────────────────────────────────────────────

    async def create_job(
        self, job_id: str, job_type: str, config: dict[str, Any] | None = None
    ) -> None:
        now = self._now()
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO jobs (id, type, status, config, created_at, updated_at) VALUES (?, ?, 'pending', ?, ?, ?)",
            (job_id, job_type, json.dumps(config or {}), now, now),
        )
        await self._db.commit()

    async def update_job(
        self,
        job_id: str,
        status: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        assert self._db is not None
        updates, params = [], []
        if status:
            updates.append("status = ?")
            params.append(status)
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result))
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        updates.append("updated_at = ?")
        params.append(self._now())
        params.append(job_id)
        await self._db.execute(
            f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params
        )
        await self._db.commit()

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    async def list_jobs(self, job_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        assert self._db is not None
        if job_type:
            query = "SELECT * FROM jobs WHERE type = ? ORDER BY created_at DESC LIMIT ?"
            params: tuple = (job_type, limit)
        else:
            query = "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?"
            params = (limit,)
        async with self._db.execute(query, params) as cursor:
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) async for row in cursor]

    # ── Datasets ──────────────────────────────────────────────────────────────

    async def register_dataset(
        self, dataset_id: str, name: str, path: str,
        constitution: str = "", num_samples: int = 0, fmt: str = "jsonl",
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT OR REPLACE INTO datasets (id, name, path, constitution, num_samples, format, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (dataset_id, name, path, constitution, num_samples, fmt, self._now()),
        )
        await self._db.commit()

    async def list_datasets(self) -> list[dict[str, Any]]:
        assert self._db is not None
        async with self._db.execute("SELECT * FROM datasets ORDER BY created_at DESC") as cursor:
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) async for row in cursor]

    # ── Checkpoints ───────────────────────────────────────────────────────────

    async def save_checkpoint(
        self, ckpt_id: str, job_id: str, path: str,
        step: int = 0, metrics: dict[str, Any] | None = None,
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO checkpoints (id, job_id, path, step, metrics, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ckpt_id, job_id, path, step, json.dumps(metrics or {}), self._now()),
        )
        await self._db.commit()

    # ── Eval Results ──────────────────────────────────────────────────────────

    async def save_eval_result(
        self, eval_id: str, model_path: str, benchmark: str, scores: dict[str, Any],
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO eval_results (id, model_path, benchmark, scores, created_at) VALUES (?, ?, ?, ?, ?)",
            (eval_id, model_path, benchmark, json.dumps(scores), self._now()),
        )
        await self._db.commit()

    async def list_eval_results(self, limit: int = 50) -> list[dict[str, Any]]:
        assert self._db is not None
        async with self._db.execute(
            "SELECT * FROM eval_results ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) async for row in cursor]
