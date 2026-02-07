# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Tests for judge systems."""

from foundry.evaluator.judges.prometheus import PrometheusJudge, JudgmentResult
from foundry.evaluator.judges.rule_judge import RuleJudge


def test_prometheus_parse_direct():
    text = "[SCORE]: 4\n[JUSTIFICATION]: Good response with minor gaps."
    result = PrometheusJudge._parse_direct(text)
    assert result.raw_score == 4
    assert result.score == 0.75  # (4-1)/4
    assert "Good response" in result.justification


def test_prometheus_parse_pairwise():
    text = "[WINNER]: A\n[JUSTIFICATION]: Response A is more detailed."
    result = PrometheusJudge._parse_pairwise(text)
    assert result.winner == "A"
    assert result.score == 1.0


def test_prometheus_parse_pairwise_b():
    text = "[WINNER]: B\n[JUSTIFICATION]: B is better."
    result = PrometheusJudge._parse_pairwise(text)
    assert result.winner == "B"
    assert result.score == 0.0


def test_rule_judge_contains():
    judge = RuleJudge(rules=[
        {"type": "contains", "keywords": ["hello", "world"], "name": "greeting"},
    ])
    result = judge.assess("hello world")
    assert result.score == 1.0


def test_rule_judge_regex():
    judge = RuleJudge(rules=[
        {"type": "regex", "pattern": r"\d{3}", "name": "has_number"},
    ])
    assert judge.assess("code 123 here").score == 1.0
    assert judge.assess("no number").score == 0.0


def test_rule_judge_json():
    judge = RuleJudge(rules=[
        {"type": "json_valid", "name": "valid_json"},
    ])
    assert judge.assess('{"key": "value"}').score == 1.0
    assert judge.assess("not json").score == 0.0


def test_rule_judge_forbidden():
    judge = RuleJudge(rules=[
        {"type": "no_forbidden", "forbidden": ["password", "secret"], "name": "no_secrets"},
    ])
    assert judge.assess("This is safe text").score == 1.0
    assert judge.assess("The password is 1234").score == 0.0


def test_rule_judge_multiple_rules():
    judge = RuleJudge(rules=[
        {"type": "min_length", "min": 10, "name": "length"},
        {"type": "contains", "keywords": ["hello"], "name": "greeting"},
    ])
    result = judge.assess("hello world, how are you?")
    assert result.score == 1.0

    result = judge.assess("hi")  # Too short and missing keyword
    assert result.score < 1.0


def test_rule_judge_no_rules():
    judge = RuleJudge()
    assert judge.assess("anything").score == 1.0
