# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Dataset Manager — Storage, versioning, and format conversion."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DatasetManager:
    """Manages dataset storage, versioning, and format conversion."""

    def __init__(self, base_dir: Path | None = None) -> None:
        from foundry.config.settings import get_settings

        self.base_dir = base_dir or get_settings().dataset_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_jsonl(self, samples: list[dict[str, Any]], name: str) -> Path:
        """Save samples as JSONL."""
        path = self.base_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        logger.info("Saved %d samples to %s", len(samples), path)
        return path

    def load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        """Load samples from JSONL."""
        samples = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        return samples

    def to_hf_dataset(self, path: Path) -> Any:
        """Convert JSONL to HuggingFace Dataset."""
        from datasets import Dataset

        samples = self.load_jsonl(path)
        return Dataset.from_list(samples)

    def save_parquet(self, samples: list[dict[str, Any]], name: str) -> Path:
        """Save samples as Parquet via HuggingFace datasets."""
        from datasets import Dataset

        ds = Dataset.from_list(samples)
        path = self.base_dir / f"{name}.parquet"
        ds.to_parquet(str(path))
        logger.info("Saved %d samples to %s", len(samples), path)
        return path

    def list_datasets(self) -> list[dict[str, Any]]:
        """List all datasets in the base directory."""
        datasets = []
        for ext in ("*.jsonl", "*.parquet", "*.arrow"):
            for path in self.base_dir.rglob(ext):
                stat = path.stat()
                datasets.append({
                    "name": path.stem,
                    "path": str(path),
                    "format": path.suffix.lstrip("."),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                })
        return datasets
