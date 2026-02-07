# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""RL-CAI Pipeline — Reinforcement Learning with Constitutional AI.

Generates preference pairs (chosen/rejected) for DPO training.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from foundry.data_engine.constitution import Constitution
from foundry.data_engine.teachers.base import Message, Teacher

logger = logging.getLogger(__name__)


@dataclass
class PreferencePair:
    """A preference pair for DPO training."""

    prompt: str
    chosen: str
    rejected: str
    principle: str
    chosen_score: float = 0.0
    rejected_score: float = 0.0

    def to_dpo_format(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "chosen": [
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": self.chosen},
            ],
            "rejected": [
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": self.rejected},
            ],
            "metadata": {
                "pipeline": "rl_cai",
                "principle": self.principle,
            },
        }


class RLCAIPipeline:
    """RL-CAI pipeline for generating DPO preference pairs.

    1. Generate two responses to the same prompt
    2. Use the constitution to judge which is better
    3. Output (chosen, rejected) pairs
    """

    JUDGE_TEMPLATE = """You are judging two responses against this principle: "{principle}"

Prompt: {prompt}

Response A:
{response_a}

Response B:
{response_b}

Which response better adheres to the principle? Answer with ONLY "A" or "B", followed by a brief justification."""

    def __init__(
        self,
        teacher: Teacher,
        constitution: Constitution,
        responses_per_prompt: int = 2,
    ) -> None:
        self.teacher = teacher
        self.constitution = constitution
        self.responses_per_prompt = responses_per_prompt

    async def generate_pair(self, prompt: str) -> PreferencePair | None:
        """Generate a single preference pair for a prompt."""
        system = self.constitution.system_prompt or "You are a helpful assistant."

        # Generate two responses
        r_a = await self.teacher.generate(
            [Message(role="system", content=system), Message(role="user", content=prompt)],
            temperature=0.9,
        )
        r_b = await self.teacher.generate(
            [Message(role="system", content=system), Message(role="user", content=prompt)],
            temperature=0.9,
        )

        if r_a.content == r_b.content:
            logger.debug("Identical responses, skipping")
            return None

        # Judge using the top principle
        principle = self.constitution.weighted_principles()[0]
        judge_prompt = self.JUDGE_TEMPLATE.format(
            principle=principle.description,
            prompt=prompt,
            response_a=r_a.content,
            response_b=r_b.content,
        )

        judgment = await self.teacher.generate(
            [Message(role="user", content=judge_prompt)],
            temperature=0.1,
            max_tokens=256,
        )

        # Parse judgment
        text = judgment.content.strip().upper()
        if text.startswith("A"):
            chosen, rejected = r_a.content, r_b.content
        elif text.startswith("B"):
            chosen, rejected = r_b.content, r_a.content
        else:
            logger.warning("Ambiguous judgment: %s", judgment.content[:100])
            return None

        return PreferencePair(
            prompt=prompt,
            chosen=chosen,
            rejected=rejected,
            principle=principle.name,
        )

    async def process_batch(
        self, prompts: list[str], on_progress: Any = None,
    ) -> list[PreferencePair]:
        """Generate preference pairs for a batch of prompts."""
        results = []
        for i, prompt in enumerate(prompts):
            try:
                pair = await self.generate_pair(prompt)
                if pair:
                    results.append(pair)
                if on_progress:
                    await on_progress(i + 1, len(prompts), pair)
            except Exception as e:
                logger.error("Failed to generate pair %d: %s", i, e)
        return results
