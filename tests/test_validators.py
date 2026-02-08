# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for output validators."""

from foundry.sandbox.validators import (
    ExactMatchValidator,
    NumericMatchValidator,
    CodeCompilationValidator,
    FormatValidator,
    ContainsValidator,
    get_validator,
)


def test_exact_match():
    v = ExactMatchValidator()
    assert v.validate("hello", "hello").passed
    assert not v.validate("hello", "world").passed


def test_exact_match_case_insensitive():
    v = ExactMatchValidator(case_insensitive=True)
    assert v.validate("Hello", "hello").passed


def test_exact_match_strip():
    v = ExactMatchValidator(strip=True)
    assert v.validate("  hello  ", "hello").passed


def test_numeric_match():
    v = NumericMatchValidator(tolerance=0.01)
    assert v.validate("3.14", 3.14).passed
    assert v.validate("3.15", 3.14).passed  # Within tolerance
    assert not v.validate("5.0", 3.14).passed


def test_numeric_extract():
    v = NumericMatchValidator(tolerance=1.0)
    assert v.validate("The answer is 42.", 42).passed


def test_code_compilation():
    v = CodeCompilationValidator()
    assert v.validate("x = 1 + 2").passed
    assert not v.validate("def foo(").passed


def test_json_format():
    v = FormatValidator(json_schema=True)
    assert v.validate('{"key": "value"}').passed
    assert not v.validate("not json").passed


def test_regex_format():
    v = FormatValidator(pattern=r"\d{3}-\d{4}")
    assert v.validate("Call 555-1234").passed
    assert not v.validate("no number here").passed


def test_contains_validator():
    v = ContainsValidator()
    result = v.validate("Hello world foo bar", ["hello", "world"])
    assert result.passed
    assert result.score == 1.0


def test_contains_partial():
    v = ContainsValidator()
    result = v.validate("Hello world", ["hello", "missing"])
    assert not result.passed
    assert result.score == 0.5


def test_get_validator():
    v = get_validator("exact")
    assert isinstance(v, ExactMatchValidator)

    v = get_validator("numeric", tolerance=0.1)
    assert isinstance(v, NumericMatchValidator)
