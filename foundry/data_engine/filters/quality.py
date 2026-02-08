# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Quality Filters — Perplexity, length, deduplication."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class QualityFilter:
    """Filter training samples by quality metrics."""

    def __init__(
        self,
        min_length: int = 50,
        max_length: int = 50000,
        min_turns: int = 1,
        dedup: bool = True,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.min_turns = min_turns
        self.dedup = dedup
        self._seen_hashes: set[str] = set()

    def _hash_sample(self, sample: dict[str, Any]) -> str:
        messages = sample.get("messages", [])
        text = " ".join(m.get("content", "") for m in messages)
        return hashlib.md5(text.encode()).hexdigest()

    def filter(self, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter a list of samples, returning only those that pass."""
        passed = []
        for sample in samples:
            messages = sample.get("messages", [])

            # Length check
            total_len = sum(len(m.get("content", "")) for m in messages)
            if total_len < self.min_length or total_len > self.max_length:
                continue

            # Turn count check
            if len(messages) < self.min_turns:
                continue

            # Deduplication
            if self.dedup:
                h = self._hash_sample(sample)
                if h in self._seen_hashes:
                    continue
                self._seen_hashes.add(h)

            passed.append(sample)

        logger.info("Quality filter: %d/%d passed", len(passed), len(samples))
        return passed
