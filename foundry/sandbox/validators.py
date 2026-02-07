# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Output Validators — Verify sandbox execution results against expected outcomes.

Used by both the Data Engine (verifiable trajectories) and Evaluator (RLVR rewards).
"""

from __future__ import annotations

import json
import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """Result of output validation."""

    passed: bool
    score: float  # 0.0 to 1.0
    reason: str = ""


class OutputValidator(ABC):
    """Base class for output validators."""

    @abstractmethod
    def validate(self, actual: str, expected: Any) -> ValidationResult:
        ...


class ExactMatchValidator(OutputValidator):
    """Validates exact string match (with optional normalization)."""

    def __init__(self, strip: bool = True, case_insensitive: bool = False) -> None:
        self.strip = strip
        self.case_insensitive = case_insensitive

    def validate(self, actual: str, expected: Any) -> ValidationResult:
        a = actual
        e = str(expected)
        if self.strip:
            a, e = a.strip(), e.strip()
        if self.case_insensitive:
            a, e = a.lower(), e.lower()
        passed = a == e
        return ValidationResult(passed=passed, score=1.0 if passed else 0.0)


class NumericMatchValidator(OutputValidator):
    """Validates numeric output within tolerance."""

    def __init__(self, tolerance: float = 1e-6, relative: bool = False) -> None:
        self.tolerance = tolerance
        self.relative = relative

    def validate(self, actual: str, expected: Any) -> ValidationResult:
        try:
            actual_num = self._extract_number(actual.strip())
            expected_num = float(expected)
        except (ValueError, TypeError):
            return ValidationResult(passed=False, score=0.0, reason="Could not parse numeric value")

        if self.relative and expected_num != 0:
            diff = abs(actual_num - expected_num) / abs(expected_num)
        else:
            diff = abs(actual_num - expected_num)

        passed = diff <= self.tolerance
        score = max(0.0, 1.0 - diff / max(self.tolerance, 1e-10))
        return ValidationResult(passed=passed, score=min(1.0, score))

    @staticmethod
    def _extract_number(text: str) -> float:
        """Extract the first number from text."""
        match = re.search(r"-?\d+\.?\d*(?:e[+-]?\d+)?", text, re.IGNORECASE)
        if match:
            return float(match.group())
        raise ValueError(f"No number found in: {text}")


class CodeCompilationValidator(OutputValidator):
    """Validates that code compiles/parses without errors."""

    def validate(self, actual: str, expected: Any = None) -> ValidationResult:
        try:
            compile(actual, "<sandbox>", "exec")
            return ValidationResult(passed=True, score=1.0)
        except SyntaxError as e:
            return ValidationResult(
                passed=False, score=0.0, reason=f"SyntaxError: {e.msg} at line {e.lineno}"
            )


class FormatValidator(OutputValidator):
    """Validates output matches an expected format (regex or JSON schema)."""

    def __init__(self, pattern: str | None = None, json_schema: bool = False) -> None:
        self.pattern = pattern
        self.json_schema = json_schema

    def validate(self, actual: str, expected: Any = None) -> ValidationResult:
        if self.json_schema:
            return self._validate_json(actual)
        if self.pattern:
            return self._validate_regex(actual)
        return ValidationResult(passed=True, score=1.0)

    def _validate_json(self, actual: str) -> ValidationResult:
        try:
            json.loads(actual.strip())
            return ValidationResult(passed=True, score=1.0)
        except json.JSONDecodeError as e:
            return ValidationResult(passed=False, score=0.0, reason=f"Invalid JSON: {e}")

    def _validate_regex(self, actual: str) -> ValidationResult:
        if self.pattern and re.search(self.pattern, actual):
            return ValidationResult(passed=True, score=1.0)
        return ValidationResult(
            passed=False, score=0.0, reason=f"Output does not match pattern: {self.pattern}"
        )


class ContainsValidator(OutputValidator):
    """Validates that output contains all expected substrings."""

    def __init__(self, case_insensitive: bool = True) -> None:
        self.case_insensitive = case_insensitive

    def validate(self, actual: str, expected: Any) -> ValidationResult:
        if isinstance(expected, str):
            expected_list = [expected]
        elif isinstance(expected, list):
            expected_list = expected
        else:
            expected_list = [str(expected)]

        a = actual.lower() if self.case_insensitive else actual
        matched = 0
        for item in expected_list:
            e = item.lower() if self.case_insensitive else item
            if e in a:
                matched += 1

        score = matched / len(expected_list) if expected_list else 1.0
        return ValidationResult(
            passed=score == 1.0,
            score=score,
            reason=f"Matched {matched}/{len(expected_list)} expected items",
        )


# ── Registry ──────────────────────────────────────────────────────────────────

VALIDATORS: dict[str, type[OutputValidator]] = {
    "exact": ExactMatchValidator,
    "numeric": NumericMatchValidator,
    "compile": CodeCompilationValidator,
    "format": FormatValidator,
    "contains": ContainsValidator,
}


def get_validator(name: str, **kwargs: Any) -> OutputValidator:
    """Get a validator by name with optional configuration."""
    cls = VALIDATORS.get(name)
    if cls is None:
        raise ValueError(f"Unknown validator: {name}. Available: {list(VALIDATORS.keys())}")
    return cls(**kwargs)
