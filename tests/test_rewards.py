# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Tests for GRPO reward functions."""

from foundry.evaluator.rewards.functions import (
    format_reward,
    tool_use_reward,
    _extract_code,
    _heuristic_quality_score,
)


def test_format_reward_with_thinking():
    rewards = format_reward(
        ["test"],
        ["<thinking>Let me analyze this</thinking>\nStep 1: First\nStep 2: Second\nTherefore, the answer is 42."],
    )
    assert len(rewards) == 1
    assert rewards[0] > 0.5


def test_format_reward_unstructured():
    rewards = format_reward(["test"], ["just some text"])
    assert len(rewards) == 1
    assert rewards[0] < 0.5


def test_tool_use_reward_complete():
    text = "<tool_call>python_exec</tool_call><tool_result>success</tool_result><thinking>reasoning</thinking>"
    rewards = tool_use_reward(["test"], [text])
    assert rewards[0] == 1.0


def test_tool_use_reward_none():
    rewards = tool_use_reward(["test"], ["just plain text"])
    assert rewards[0] == 0.0


def test_extract_code_fenced():
    text = "Here is code:\n```python\nprint('hello')\n```"
    code = _extract_code(text)
    assert "print('hello')" in code


def test_extract_code_tagged():
    text = "<code>x = 42</code>"
    code = _extract_code(text)
    assert "x = 42" in code


def test_extract_code_none():
    code = _extract_code("no code here, just words")
    assert code == ""


def test_heuristic_quality():
    good = "First, let me analyze the problem. Then, I'll consider the options. Finally, here is my conclusion with several supporting points that demonstrate reasoning."
    bad = "ok"
    assert _heuristic_quality_score(good) > _heuristic_quality_score(bad)
