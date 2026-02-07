# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Rule-based Judge — Regex, keyword, and format validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from foundry.evaluator.judges.prometheus import JudgmentResult


class RuleJudge:
    """Rule-based evaluator for structured outputs."""

    def __init__(self, rules: list[dict[str, Any]] | None = None) -> None:
        self.rules = rules or []

    def assess(self, response: str) -> JudgmentResult:
        """Evaluate response against all rules."""
        if not self.rules:
            return JudgmentResult(score=1.0)

        scores = []
        reasons = []

        for rule in self.rules:
            rule_type = rule.get("type", "contains")
            passed = False

            if rule_type == "contains":
                keywords = rule.get("keywords", [])
                passed = all(kw.lower() in response.lower() for kw in keywords)

            elif rule_type == "regex":
                pattern = rule.get("pattern", "")
                passed = bool(re.search(pattern, response))

            elif rule_type == "json_valid":
                try:
                    json.loads(response)
                    passed = True
                except json.JSONDecodeError:
                    passed = False

            elif rule_type == "min_length":
                passed = len(response) >= rule.get("min", 0)

            elif rule_type == "max_length":
                passed = len(response) <= rule.get("max", float("inf"))

            elif rule_type == "no_forbidden":
                forbidden = rule.get("forbidden", [])
                passed = not any(f.lower() in response.lower() for f in forbidden)

            scores.append(1.0 if passed else 0.0)
            if not passed:
                reasons.append(f"Failed rule: {rule.get('name', rule_type)}")

        avg_score = sum(scores) / len(scores) if scores else 0.0
        return JudgmentResult(
            score=avg_score,
            justification="; ".join(reasons) if reasons else "All rules passed",
        )
