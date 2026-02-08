# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""LLM Judge — Use any local or API model as a judge."""

from __future__ import annotations

import logging
import re
from typing import Any

from foundry.evaluator.judges.prometheus import JudgmentResult

logger = logging.getLogger(__name__)

SIMPLE_JUDGE_TEMPLATE = """Rate the following response on a scale of 1 to 5 for {criteria}.

Prompt: {prompt}

Response: {response}

Score (1-5):"""


class LLMJudge:
    """Generic LLM-as-Judge using any Teacher model."""

    def __init__(self, teacher: Any) -> None:
        self.teacher = teacher

    async def assess(
        self,
        prompt: str,
        response: str,
        criteria: str = "quality",
    ) -> JudgmentResult:
        from foundry.data_engine.teachers.base import Message

        judge_prompt = SIMPLE_JUDGE_TEMPLATE.format(
            criteria=criteria, prompt=prompt, response=response,
        )
        result = await self.teacher.generate(
            [Message(role="user", content=judge_prompt)],
            temperature=0.1,
            max_tokens=128,
        )

        # Parse score
        match = re.search(r"(\d)", result.content)
        raw_score = int(match.group(1)) if match else 3
        raw_score = max(1, min(5, raw_score))

        return JudgmentResult(
            score=(raw_score - 1) / 4.0,
            raw_score=raw_score,
            justification=result.content,
        )
