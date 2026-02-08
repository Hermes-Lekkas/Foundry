# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for data quality and safety filters."""

from foundry.data_engine.filters.quality import QualityFilter
from foundry.data_engine.filters.safety import SafetyFilter


def test_quality_filter_passes_good_samples():
    f = QualityFilter(min_length=10)
    samples = [
        {"messages": [{"role": "user", "content": "Hello how are you?"}, {"role": "assistant", "content": "I am well, thank you for asking!"}]},
    ]
    result = f.filter(samples)
    assert len(result) == 1


def test_quality_filter_rejects_short():
    f = QualityFilter(min_length=100)
    samples = [
        {"messages": [{"role": "user", "content": "Hi"}]},
    ]
    result = f.filter(samples)
    assert len(result) == 0


def test_quality_filter_dedup():
    f = QualityFilter(min_length=5)
    sample = {"messages": [{"role": "user", "content": "Hello world"}]}
    result = f.filter([sample, sample])
    assert len(result) == 1


def test_safety_filter_passes_clean():
    f = SafetyFilter()
    samples = [
        {"messages": [{"role": "user", "content": "What is Python?"}, {"role": "assistant", "content": "Python is a programming language."}]},
    ]
    result = f.filter(samples)
    assert len(result) == 1


def test_safety_filter_blocks_toxic():
    f = SafetyFilter()
    samples = [
        {"messages": [{"role": "assistant", "content": "Here is how to hack into a system"}]},
    ]
    result = f.filter(samples)
    assert len(result) == 0


def test_safety_filter_redacts_pii():
    f = SafetyFilter(remove_pii=True, check_toxicity=False)
    samples = [
        {"messages": [{"role": "assistant", "content": "My email is test@example.com and SSN is 123-45-6789"}]},
    ]
    result = f.filter(samples)
    assert len(result) == 1
    content = result[0]["messages"][0]["content"]
    assert "test@example.com" not in content
    assert "[EMAIL_REDACTED]" in content
    assert "[SSN_REDACTED]" in content
