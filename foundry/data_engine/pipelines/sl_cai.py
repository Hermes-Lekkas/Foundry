# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""SL-CAI Pipeline — Supervised Learning with Constitutional AI.

Generate -> Critique -> Revise -> produce fine-tuning data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from foundry.data_engine.constitution import Constitution, Principle
from foundry.data_engine.teachers.base import Message, Teacher

logger = logging.getLogger(__name__)


@dataclass
class SLCAISample:
    """A single SL-CAI training sample."""

    prompt: str
    original_response: str
    critiques: list[dict[str, str]]
    revised_response: str
    principles_applied: list[str]

    def to_chat_format(self) -> dict[str, Any]:
        """Convert to chat format for SFT training."""
        return {
            "messages": [
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": self.revised_response},
            ],
            "metadata": {
                "pipeline": "sl_cai",
                "principles": self.principles_applied,
                "num_revisions": len(self.critiques),
            },
        }


class SLCAIPipeline:
    """Supervised Learning Constitutional AI pipeline.

    1. Generate initial response to a prompt
    2. Critique against each constitutional principle
    3. Revise based on critiques
    4. Output the revised response as training data
    """

    def __init__(
        self,
        teacher: Teacher,
        constitution: Constitution,
        max_revisions: int = 3,
    ) -> None:
        self.teacher = teacher
        self.constitution = constitution
        self.max_revisions = max_revisions

    async def process_prompt(self, prompt: str) -> SLCAISample:
        """Run the full SL-CAI pipeline on a single prompt."""
        # Step 1: Generate initial response
        system = self.constitution.system_prompt or "You are a helpful assistant."
        response = await self.teacher.generate([
            Message(role="system", content=system),
            Message(role="user", content=prompt),
        ])
        current_response = response.content

        # Step 2 & 3: Critique and revise for each principle
        critiques = []
        principles_applied = []

        for principle in self.constitution.weighted_principles()[:self.max_revisions]:
            critique = await self.teacher.critique(
                current_response,
                principle.description,
                principle.critique_template,
            )
            critiques.append({
                "principle": principle.name,
                "critique": critique,
            })

            revised = await self.teacher.revise(
                current_response,
                critique,
                principle.revision_template,
            )
            current_response = revised
            principles_applied.append(principle.name)

        return SLCAISample(
            prompt=prompt,
            original_response=response.content,
            critiques=critiques,
            revised_response=current_response,
            principles_applied=principles_applied,
        )

    async def process_batch(
        self, prompts: list[str], on_progress: Any = None,
    ) -> list[SLCAISample]:
        """Process a batch of prompts through SL-CAI."""
        results = []
        for i, prompt in enumerate(prompts):
            try:
                sample = await self.process_prompt(prompt)
                results.append(sample)
                if on_progress:
                    await on_progress(i + 1, len(prompts), sample)
            except Exception as e:
                logger.error("Failed to process prompt %d: %s", i, e)
        return results
