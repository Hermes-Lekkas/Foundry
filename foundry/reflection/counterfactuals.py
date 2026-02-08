# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Counterfactual Engine — Generates semantic variants to test causal understanding."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Counterfactual:
    """A counterfactual variant of a problem."""
    
    original_question: str
    modified_question: str
    expected_answer: str
    transformation_type: str
    changed_aspect: str
    reasoning_constraint: str


@dataclass
class ReasoningProblem:
    """A problem with its reasoning trace."""
    
    question: str
    answer: str
    explanation: str
    domain: str = "math"  # math, code, logic, etc.
    
    def extract_numbers(self) -> list[float]:
        """Extract numerical values from the question."""
        numbers = re.findall(r'\b\d+\.?\d*\b', self.question)
        return [float(n) for n in numbers]


class TransformationStrategy(ABC):
    """Base class for counterfactual transformation strategies."""
    
    @abstractmethod
    def apply(
        self,
        problem: ReasoningProblem,
        explanation: str
    ) -> Optional[Counterfactual]:
        """Apply transformation to generate counterfactual."""
        pass
    
    @abstractmethod
    def compute_expected(
        self,
        original: ReasoningProblem,
        counterfactual: str
    ) -> str:
        """Compute expected answer for counterfactual."""
        pass


class ValueMutation(TransformationStrategy):
    """Change numerical values while preserving structure."""
    
    def apply(
        self,
        problem: ReasoningProblem,
        explanation: str
    ) -> Optional[Counterfactual]:
        numbers = problem.extract_numbers()
        if len(numbers) < 2:
            return None
        
        # Change the first number
        old_val = numbers[0]
        new_val = old_val * 2  # Simple doubling
        
        modified = problem.question.replace(
            str(int(old_val)) if old_val == int(old_val) else str(old_val),
            str(int(new_val)) if new_val == int(new_val) else str(new_val),
            1
        )
        
        return Counterfactual(
            original_question=problem.question,
            modified_question=modified,
            expected_answer=self.compute_expected(problem, modified),
            transformation_type="value_mutation",
            changed_aspect=f"Changed {old_val} to {new_val}",
            reasoning_constraint="Must maintain same operation structure"
        )
    
    def compute_expected(self, original: ReasoningProblem, counterfactual: str) -> str:
        # Try to extract the operation from explanation
        # This is a simplified version - real version would use the model
        orig_nums = original.extract_numbers()
        cf_nums = [float(n) for n in re.findall(r'\b\d+\.?\d*\b', counterfactual)]
        
        if len(orig_nums) >= 2 and len(cf_nums) >= 2:
            # If original was addition, counterfactual should be addition
            orig_result = float(original.answer) if original.answer.replace('.','').isdigit() else 0
            if abs(orig_nums[0] + orig_nums[1] - orig_result) < 0.01:
                return str(cf_nums[0] + cf_nums[1])
            elif abs(orig_nums[0] * orig_nums[1] - orig_result) < 0.01:
                return str(cf_nums[0] * cf_nums[1])
        
        return "[computed]"


class ConstraintInversion(TransformationStrategy):
    """Flip constraints (max→min, before→after, etc.)."""
    
    INVERSIONS = {
        "maximum": "minimum",
        "minimum": "maximum",
        "before": "after",
        "after": "before",
        "more than": "less than",
        "less than": "more than",
        "increase": "decrease",
        "decrease": "increase",
    }
    
    def apply(
        self,
        problem: ReasoningProblem,
        explanation: str
    ) -> Optional[Counterfactual]:
        modified = problem.question
        changed = None
        
        for old, new in self.INVERSIONS.items():
            if old in problem.question.lower():
                modified = re.sub(old, new, modified, flags=re.IGNORECASE)
                changed = f"{old} -> {new}"
                break
        
        if modified == problem.question:
            return None
        
        return Counterfactual(
            original_question=problem.question,
            modified_question=modified,
            expected_answer="[requires_semantic_analysis]",
            transformation_type="constraint_inversion",
            changed_aspect=changed or "inverted constraint",
            reasoning_constraint="Must recognize inverted logic"
        )
    
    def compute_expected(self, original: ReasoningProblem, counterfactual: str) -> str:
        # This requires deeper semantic understanding
        return "[semantic_analysis_required]"


class BoundaryTesting(TransformationStrategy):
    """Test edge cases and boundary conditions."""
    
    def apply(
        self,
        problem: ReasoningProblem,
        explanation: str
    ) -> Optional[Counterfactual]:
        numbers = problem.extract_numbers()
        if not numbers:
            return None
        
        # Test with zero
        old_val = numbers[0]
        if old_val == 0:
            return None
        
        modified = problem.question.replace(
            str(int(old_val)) if old_val == int(old_val) else str(old_val),
            "0",
            1
        )
        
        return Counterfactual(
            original_question=problem.question,
            modified_question=modified,
            expected_answer="0" if "multiply" in explanation.lower() else "[depends]",
            transformation_type="boundary_zero",
            changed_aspect=f"Changed {old_val} to 0 (boundary test)",
            reasoning_constraint="Must handle zero correctly"
        )
    
    def compute_expected(self, original: ReasoningProblem, counterfactual: str) -> str:
        return "[context_dependent]"


class UnitTransformation(TransformationStrategy):
    """Change units to test dimensional understanding."""
    
    UNITS = {
        "km": "miles",
        "miles": "km",
        "hours": "minutes",
        "minutes": "hours",
        "kg": "pounds",
        "pounds": "kg",
    }
    
    def apply(
        self,
        problem: ReasoningProblem,
        explanation: str
    ) -> Optional[Counterfactual]:
        modified = problem.question
        changed = None
        
        for old_unit, new_unit in self.UNITS.items():
            if old_unit in problem.question.lower():
                modified = re.sub(old_unit, new_unit, modified, flags=re.IGNORECASE)
                changed = f"{old_unit} -> {new_unit}"
                break
        
        if modified == problem.question:
            return None
        
        return Counterfactual(
            original_question=problem.question,
            modified_question=modified,
            expected_answer="[unit_conversion_required]",
            transformation_type="unit_change",
            changed_aspect=changed or "changed units",
            reasoning_constraint="Must understand dimensional analysis"
        )
    
    def compute_expected(self, original: ReasoningProblem, counterfactual: str) -> str:
        return "[conversion_calculation]"


class CounterfactualEngine:
    """Generates counterfactuals to test causal understanding."""
    
    def __init__(self):
        self.strategies: list[TransformationStrategy] = [
            ValueMutation(),
            ConstraintInversion(),
            BoundaryTesting(),
            UnitTransformation(),
        ]
    
    def generate(
        self,
        question: str,
        answer: str,
        explanation: str,
        max_counterfactuals: int = 5
    ) -> list[Counterfactual]:
        """Generate counterfactual variants of a problem."""
        problem = ReasoningProblem(
            question=question,
            answer=answer,
            explanation=explanation
        )
        
        counterfactuals = []
        for strategy in self.strategies:
            try:
                cf = strategy.apply(problem, explanation)
                if cf and self._is_valid(cf):
                    counterfactuals.append(cf)
                    
                if len(counterfactuals) >= max_counterfactuals:
                    break
            except Exception:
                continue
        
        return counterfactuals
    
    def _is_valid(self, counterfactual: Counterfactual) -> bool:
        """Check if counterfactual is semantically valid."""
        # Must be different from original
        if counterfactual.modified_question == counterfactual.original_question:
            return False
        
        # Must still be answerable
        if len(counterfactual.modified_question) < 10:
            return False
        
        return True
