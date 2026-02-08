# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Prometheus 2 Judge — Direct assessment and pairwise ranking.

Prometheus evaluates responses using a rubric-based scoring system,
providing both numeric scores (1-5) and detailed justifications.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DIRECT_ASSESSMENT_TEMPLATE = """You are a fair evaluator. Score the following response on a scale of 1-5 based on the given criteria.

**Criteria:** {criteria}

**Rubric:**
- 5 (Excellent): Fully meets all criteria with high quality
- 4 (Good): Meets most criteria with minor gaps
- 3 (Adequate): Partially meets criteria with noticeable gaps
- 2 (Poor): Fails to meet most criteria
- 1 (Very Poor): Does not address the criteria at all

**Prompt:** {prompt}

**Response:** {response}

Provide your evaluation in this exact format:
[SCORE]: <number 1-5>
[JUSTIFICATION]: <brief explanation>"""

PAIRWISE_TEMPLATE = """You are a fair evaluator. Compare the two responses below and determine which better meets the criteria.

**Criteria:** {criteria}

**Prompt:** {prompt}

**Response A:** {response_a}

**Response B:** {response_b}

Which response is better? Answer in this exact format:
[WINNER]: <A or B>
[JUSTIFICATION]: <brief explanation>"""


@dataclass
class JudgmentResult:
    """Result of a judge evaluation."""

    score: float  # 0.0 to 1.0 (normalized)
    raw_score: int = 0  # 1-5 for direct assessment
    justification: str = ""
    winner: str = ""  # A or B for pairwise


class PrometheusJudge:
    """Prometheus 2 style evaluator using LLM-as-judge with rubrics."""

    def __init__(self, teacher: Any | None = None) -> None:
        self._teacher = teacher

    async def _get_teacher(self) -> Any:
        if self._teacher is not None:
            return self._teacher
        from foundry.data_engine.teachers.api_teacher import APITeacher
        from foundry.config.settings import get_settings

        settings = get_settings()
        self._teacher = APITeacher(
            provider=settings.teacher_provider,
            model=settings.teacher_model,
        )
        return self._teacher

    async def direct_assess(
        self,
        prompt: str,
        response: str,
        criteria: str = "helpfulness, accuracy, and completeness",
    ) -> JudgmentResult:
        """Score a single response on a 1-5 scale."""
        from foundry.data_engine.teachers.base import Message

        teacher = await self._get_teacher()
        judge_prompt = DIRECT_ASSESSMENT_TEMPLATE.format(
            criteria=criteria, prompt=prompt, response=response,
        )
        result = await teacher.generate(
            [Message(role="user", content=judge_prompt)],
            temperature=0.1,
            max_tokens=512,
        )

        return self._parse_direct(result.content)

    async def pairwise_rank(
        self,
        prompt: str,
        response_a: str,
        response_b: str,
        criteria: str = "helpfulness, accuracy, and completeness",
    ) -> JudgmentResult:
        """Compare two responses and pick a winner."""
        from foundry.data_engine.teachers.base import Message

        teacher = await self._get_teacher()
        judge_prompt = PAIRWISE_TEMPLATE.format(
            criteria=criteria, prompt=prompt,
            response_a=response_a, response_b=response_b,
        )
        result = await teacher.generate(
            [Message(role="user", content=judge_prompt)],
            temperature=0.1,
            max_tokens=512,
        )

        return self._parse_pairwise(result.content)

    @staticmethod
    def _parse_direct(text: str) -> JudgmentResult:
        score_match = re.search(r"\[SCORE\]\s*:?\s*(\d)", text)
        just_match = re.search(r"\[JUSTIFICATION\]\s*:?\s*(.+)", text, re.DOTALL)

        raw_score = int(score_match.group(1)) if score_match else 3
        raw_score = max(1, min(5, raw_score))

        return JudgmentResult(
            score=(raw_score - 1) / 4.0,  # Normalize to 0-1
            raw_score=raw_score,
            justification=just_match.group(1).strip() if just_match else text,
        )

    @staticmethod
    def _parse_pairwise(text: str) -> JudgmentResult:
        winner_match = re.search(r"\[WINNER\]\s*:?\s*([AB])", text, re.IGNORECASE)
        just_match = re.search(r"\[JUSTIFICATION\]\s*:?\s*(.+)", text, re.DOTALL)

        winner = winner_match.group(1).upper() if winner_match else "A"

        return JudgmentResult(
            score=1.0 if winner == "A" else 0.0,
            winner=winner,
            justification=just_match.group(1).strip() if just_match else text,
        )
