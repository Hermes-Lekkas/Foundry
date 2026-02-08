# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for dataset manager."""

import tempfile
from pathlib import Path

from foundry.data_engine.storage.dataset import DatasetManager


def test_save_and_load_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DatasetManager(base_dir=Path(tmpdir))
        samples = [
            {"messages": [{"role": "user", "content": "hello"}]},
            {"messages": [{"role": "user", "content": "world"}]},
        ]
        path = dm.save_jsonl(samples, "test_dataset")
        assert path.exists()

        loaded = dm.load_jsonl(path)
        assert len(loaded) == 2
        assert loaded[0]["messages"][0]["content"] == "hello"


def test_list_datasets():
    with tempfile.TemporaryDirectory() as tmpdir:
        dm = DatasetManager(base_dir=Path(tmpdir))
        dm.save_jsonl([{"a": 1}], "ds1")
        dm.save_jsonl([{"b": 2}], "ds2")

        datasets = dm.list_datasets()
        assert len(datasets) == 2
        names = [d["name"] for d in datasets]
        assert "ds1" in names
        assert "ds2" in names
