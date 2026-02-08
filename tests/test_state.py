# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for SQLite state manager."""

import pytest
from foundry.orchestrator.state import StateManager


@pytest.fixture
async def state():
    sm = StateManager(db_path=":memory:")
    await sm.initialize()
    yield sm
    await sm.close()


@pytest.mark.asyncio
async def test_create_and_get_job(state):
    await state.create_job("job_1", "training", {"model": "test"})
    job = await state.get_job("job_1")
    assert job is not None
    assert job["type"] == "training"
    assert job["status"] == "pending"


@pytest.mark.asyncio
async def test_update_job(state):
    await state.create_job("job_2", "synthesis")
    await state.update_job("job_2", status="running")
    job = await state.get_job("job_2")
    assert job["status"] == "running"


@pytest.mark.asyncio
async def test_list_jobs(state):
    await state.create_job("j1", "training")
    await state.create_job("j2", "synthesis")
    await state.create_job("j3", "training")

    all_jobs = await state.list_jobs()
    assert len(all_jobs) == 3

    training_jobs = await state.list_jobs(job_type="training")
    assert len(training_jobs) == 2


@pytest.mark.asyncio
async def test_register_dataset(state):
    await state.register_dataset("ds_1", "test_data", "/path/to/data", num_samples=100)
    datasets = await state.list_datasets()
    assert len(datasets) == 1
    assert datasets[0]["name"] == "test_data"
    assert datasets[0]["num_samples"] == 100


@pytest.mark.asyncio
async def test_save_eval_result(state):
    await state.save_eval_result("e1", "/model/path", "gsm8k", {"score": 0.85})
    results = await state.list_eval_results()
    assert len(results) == 1
    assert results[0]["benchmark"] == "gsm8k"


@pytest.mark.asyncio
async def test_get_nonexistent_job(state):
    job = await state.get_job("nonexistent")
    assert job is None
