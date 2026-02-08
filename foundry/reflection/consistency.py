# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Consistency Checker — Verifies causal understanding through counterfactual testing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from foundry.reflection.counterfactuals import Counterfactual


@dataclass
class ConsistencyViolation:
    """A detected inconsistency in reasoning."""
    
    counterfactual_question: str
    predicted_answer: str
    expected_answer: str
    violation_type: str
    severity: str  # "minor", "major", "critical"
    description: str
    affected_concept: str


@dataclass
class ConsistencyReport:
    """Complete consistency analysis."""
    
    is_consistent: bool
    violations: list[ConsistencyViolation]
    consistency_score: float  # 0.0 to 1.0
    robustness_score: float   # Performance on counterfactuals
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "consistency_score": self.consistency_score,
            "robustness_score": self.robustness_score,
            "num_violations": len(self.violations),
            "violations": [
                {
                    "question": v.counterfactual_question,
                    "predicted": v.predicted_answer,
                    "expected": v.expected_answer,
                    "type": v.violation_type,
                    "severity": v.severity,
                    "concept": v.affected_concept,
                }
                for v in self.violations
            ],
        }


class ConsistencyChecker:
    """Checks if model predictions are causally consistent."""
    
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance
    
    def check(
        self,
        original_question: str,
        original_answer: str,
        counterfactuals: list[Counterfactual],
        counterfactual_predictions: list[str]
    ) -> ConsistencyReport:
        """Check consistency across original and counterfactuals."""
        
        violations = []
        
        for cf, prediction in zip(counterfactuals, counterfactual_predictions):
            violation = self._check_single(cf, prediction)
            if violation:
                violations.append(violation)
        
        # Calculate scores
        total = len(counterfactuals)
        correct = total - len(violations)
        robustness = correct / total if total > 0 else 1.0
        
        # Consistency considers severity
        severity_weights = {
            "critical": 1.0,
            "major": 0.5,
            "minor": 0.2
        }
        weighted_errors = sum(
            severity_weights.get(v.severity, 0.5) for v in violations
        )
        consistency = max(0.0, 1.0 - (weighted_errors / max(total, 1)))
        
        return ConsistencyReport(
            is_consistent=len(violations) == 0,
            violations=violations,
            consistency_score=consistency,
            robustness_score=robustness
        )
    
    def _check_single(
        self,
        counterfactual: Counterfactual,
        prediction: str
    ) -> Optional[ConsistencyViolation]:
        """Check a single counterfactual prediction."""
        
        expected = counterfactual.expected_answer
        
        # Skip if we can't compute expected
        if expected.startswith("[") and expected.endswith("]"):
            return None
        
        # Extract numbers from predictions
        pred_nums = self._extract_numbers(prediction)
        exp_nums = self._extract_numbers(expected)
        
        if pred_nums and exp_nums:
            # Numerical comparison
            if abs(pred_nums[0] - exp_nums[0]) > self.tolerance:
                return ConsistencyViolation(
                    counterfactual_question=counterfactual.modified_question,
                    predicted_answer=prediction,
                    expected_answer=expected,
                    violation_type="numerical_inconsistency",
                    severity=self._assess_severity(counterfactual),
                    description=f"Predicted {pred_nums[0]}, expected {exp_nums[0]}",
                    affected_concept=counterfactual.transformation_type
                )
        else:
            # Text comparison
            if prediction.strip().lower() != expected.strip().lower():
                return ConsistencyViolation(
                    counterfactual_question=counterfactual.modified_question,
                    predicted_answer=prediction,
                    expected_answer=expected,
                    violation_type="qualitative_inconsistency",
                    severity="major",
                    description="Qualitative answer mismatch",
                    affected_concept=counterfactual.transformation_type
                )
        
        return None
    
    def _extract_numbers(self, text: str) -> list[float]:
        """Extract numerical values from text."""
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return [float(n) for n in numbers]
    
    def _assess_severity(self, counterfactual: Counterfactual) -> str:
        """Assess severity of a violation."""
        if "boundary" in counterfactual.transformation_type:
            return "critical"  # Edge cases are important
        if "unit" in counterfactual.transformation_type:
            return "major"     # Dimensional analysis is fundamental
        if "constraint" in counterfactual.transformation_type:
            return "major"     # Logic errors are serious
        return "minor"
    
    def check_transitive_consistency(
        self,
        predictions: list[tuple[str, str]]  # (question, answer) pairs
    ) -> list[ConsistencyViolation]:
        """Check transitive relationships across multiple predictions."""
        # Example: If A > B and B > C, then A > C
        violations = []
        
        # Extract comparisons
        comparisons = []
        for question, answer in predictions:
            comp = self._extract_comparison(question, answer)
            if comp:
                comparisons.append(comp)
        
        # Check transitivity
        for i, (a, b, rel1) in enumerate(comparisons):
            for j, (c, d, rel2) in enumerate(comparisons):
                if i != j and b == c:
                    # Found chain: a -> b -> d
                    expected = self._combine_relations(rel1, rel2)
                    # Look for direct a -> d
                    for k, (e, f, rel3) in enumerate(comparisons):
                        if e == a and f == d:
                            if rel3 != expected:
                                violations.append(ConsistencyViolation(
                                    counterfactual_question=f"Transitivity: {a} -> {b} -> {d}",
                                    predicted_answer=rel3,
                                    expected_answer=expected,
                                    violation_type="transitive_inconsistency",
                                    severity="major",
                                    description=f"Transitivity violation: {rel1} + {rel2} should give {expected}, got {rel3}",
                                    affected_concept="transitive_reasoning"
                                ))
        
        return violations
    
    def _extract_comparison(
        self,
        question: str,
        answer: str
    ) -> Optional[tuple[str, str, str]]:
        """Extract a comparison relation from Q&A."""
        # Simple pattern matching for "X is greater than Y" type questions
        if "greater than" in question.lower() or "more than" in question.lower():
            nums = self._extract_numbers(question)
            if len(nums) >= 2:
                return (str(nums[0]), str(nums[1]), ">")
        elif "less than" in question.lower():
            nums = self._extract_numbers(question)
            if len(nums) >= 2:
                return (str(nums[0]), str(nums[1]), "<")
        return None
    
    def _combine_relations(self, rel1: str, rel2: str) -> str:
        """Combine two relations transitively."""
        if rel1 == ">" and rel2 == ">":
            return ">"
        elif rel1 == "<" and rel2 == "<":
            return "<"
        return "?"
