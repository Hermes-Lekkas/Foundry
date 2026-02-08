# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for the Constitution system."""

from pathlib import Path
from foundry.data_engine.constitution import Constitution, Principle


def test_load_agentic_constitution():
    c = Constitution.from_yaml(Path("constitutions/agentic.yaml"))
    assert c.name == "agentic"
    assert len(c.principles) == 5
    assert c.system_prompt.strip() != ""


def test_load_coding_constitution():
    c = Constitution.from_yaml(Path("constitutions/coding.yaml"))
    assert c.name == "coding"
    assert len(c.principles) >= 3


def test_load_reasoning_constitution():
    c = Constitution.from_yaml(Path("constitutions/reasoning.yaml"))
    assert c.name == "reasoning"
    assert len(c.principles) >= 3


def test_load_general_constitution():
    c = Constitution.from_yaml(Path("constitutions/general.yaml"))
    assert c.name == "general"


def test_weighted_principles():
    c = Constitution.from_yaml(Path("constitutions/agentic.yaml"))
    weighted = c.weighted_principles()
    # First should be highest weight
    assert weighted[0].weight >= weighted[-1].weight


def test_principles_for_domain():
    c = Constitution.from_yaml(Path("constitutions/agentic.yaml"))
    agentic_principles = c.principles_for_domain("agentic")
    assert len(agentic_principles) >= 1


def test_principle_render_critique():
    p = Principle(
        name="test",
        description="Be helpful",
        critique_template="Review: {{ response }}",
    )
    rendered = p.render_critique(response="Hello")
    assert "Hello" in rendered


def test_principle_render_revision():
    p = Principle(
        name="test",
        description="Be helpful",
        revision_template="Revise: {{ critique }}",
    )
    rendered = p.render_revision(critique="needs improvement")
    assert "needs improvement" in rendered


def test_from_dict():
    data = {
        "name": "custom",
        "description": "A custom constitution",
        "principles": [
            {
                "name": "clarity",
                "description": "Be clear",
                "weight": 1.5,
            }
        ],
    }
    c = Constitution.from_dict(data)
    assert c.name == "custom"
    assert len(c.principles) == 1
    assert c.principles[0].weight == 1.5
