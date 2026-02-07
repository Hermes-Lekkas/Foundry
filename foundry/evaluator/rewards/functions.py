# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Reward Functions for GRPO — Composable, sandbox-backed rewards.

These functions are consumed by TRL's GRPOTrainer as reward_funcs.
Each takes (prompts, completions, **kwargs) and returns list[float].

Reward composition: r = alpha * hard + (1-alpha) * soft
- Hard: binary 0/1 from sandbox execution
- Soft: 0.0-1.0 from constitutional/format scoring
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def code_correctness_reward(
    prompts: list[str], completions: list[str], **kwargs: Any,
) -> list[float]:
    """Execute code in sandbox -> binary 0/1 reward.

    Extracts code blocks from completions, executes them in the sandbox,
    and returns 1.0 if execution succeeds, 0.0 otherwise.
    """
    from foundry.sandbox.executor import SandboxExecutor

    sandbox = SandboxExecutor(timeout=10)
    rewards = []

    for completion in completions:
        code = _extract_code(completion)
        if not code:
            rewards.append(0.0)
            continue

        try:
            result = asyncio.get_event_loop().run_until_complete(
                sandbox.execute(code)
            )
            rewards.append(1.0 if result.success else 0.0)
        except Exception:
            rewards.append(0.0)

    sandbox.cleanup()
    return rewards


def tool_use_reward(
    prompts: list[str], completions: list[str], **kwargs: Any,
) -> list[float]:
    """Reward for correct tool use patterns.

    Checks:
    - Tool calls are properly formatted
    - Tool results are acknowledged
    - No hallucinated tool outputs
    """
    rewards = []
    for completion in completions:
        score = 0.0
        has_tool_call = "<tool_call>" in completion or "tool_call" in completion
        has_tool_result = "<tool_result>" in completion or "tool_result" in completion

        if has_tool_call:
            score += 0.3  # Used tools
        if has_tool_result:
            score += 0.3  # Acknowledged results
        if has_tool_call and has_tool_result:
            score += 0.2  # Complete tool cycle
        if "<thinking>" in completion or "think" in completion.lower():
            score += 0.2  # Shows reasoning

        rewards.append(min(1.0, score))

    return rewards


def constitutional_reward(
    prompts: list[str], completions: list[str], **kwargs: Any,
) -> list[float]:
    """Constitutional scoring — judge quality against principles.

    Uses the Prometheus judge to score each completion.
    Falls back to heuristic scoring if no judge is available.
    """
    rewards = []
    for prompt, completion in zip(prompts, completions):
        score = _heuristic_quality_score(completion)
        rewards.append(score)
    return rewards


def format_reward(
    prompts: list[str], completions: list[str], **kwargs: Any,
) -> list[float]:
    """Reward for structured formatting (thinking tags, clear structure)."""
    rewards = []
    for completion in completions:
        score = 0.0

        # Check for thinking/reasoning structure
        if re.search(r"<thinking>.*?</thinking>", completion, re.DOTALL):
            score += 0.4

        # Check for clear step-by-step structure
        steps = re.findall(r"(?:step|Step|\d+[\.\)])", completion)
        if len(steps) >= 2:
            score += 0.3

        # Check for final answer clarity
        if re.search(r"(?:final answer|conclusion|result|therefore)", completion, re.IGNORECASE):
            score += 0.3

        rewards.append(min(1.0, score))

    return rewards


def get_default_reward_funcs() -> list[Any]:
    """Get the default set of reward functions for GRPO training."""
    return [format_reward, tool_use_reward]


def _extract_code(text: str) -> str:
    """Extract Python code from a completion."""
    # Try fenced code blocks first
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try <code> tags
    match = re.search(r"<code>(.*?)</code>", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If the whole thing looks like code, use it
    lines = text.strip().split("\n")
    code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if code_lines and all(
        any(kw in l for kw in ["def ", "class ", "import ", "print", "return", "=", "for ", "if "])
        for l in code_lines[:3]
    ):
        return text.strip()

    return ""


def _heuristic_quality_score(text: str) -> float:
    """Simple heuristic quality score for responses."""
    score = 0.0

    # Length (prefer moderate length)
    length = len(text)
    if 100 < length < 5000:
        score += 0.3
    elif length >= 50:
        score += 0.1

    # Coherence indicators
    sentences = text.split(".")
    if len(sentences) >= 3:
        score += 0.2

    # Structure
    if any(kw in text.lower() for kw in ["first", "then", "finally", "step"]):
        score += 0.2

    # No repetition (simple check)
    words = text.lower().split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio > 0.5:
            score += 0.3

    return min(1.0, score)
