# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Benchmark Runner — Execute standardized evaluations against models."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark evaluation."""

    benchmark: str
    score: float
    total: int = 0
    correct: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        pct = f"{self.score * 100:.1f}%"
        return f"{self.benchmark}: {pct} ({self.correct}/{self.total})"


class BenchmarkRunner:
    """Runs standardized benchmarks against a model."""

    def __init__(self, model: Any, tokenizer: Any) -> None:
        self.model = model
        self.tokenizer = tokenizer

    async def run(self, benchmark: str = "all") -> list[BenchmarkResult]:
        """Run one or all benchmarks."""
        results = []
        benchmarks = self._resolve_benchmarks(benchmark)

        for bm in benchmarks:
            try:
                result = await self._run_single(bm)
                results.append(result)
                logger.info("Benchmark %s: %s", bm, result.summary())
            except Exception as e:
                logger.error("Benchmark %s failed: %s", bm, e)
                results.append(BenchmarkResult(benchmark=bm, score=0.0))

        return results

    def _resolve_benchmarks(self, benchmark: str) -> list[str]:
        if benchmark == "all":
            return ["gsm8k_sample", "code_quality", "tool_use"]
        return [benchmark]

    async def _run_single(self, benchmark: str) -> BenchmarkResult:
        if benchmark == "gsm8k_sample":
            return await self._run_gsm8k_sample()
        elif benchmark == "code_quality":
            return await self._run_code_quality()
        elif benchmark == "tool_use":
            return await self._run_tool_use()
        else:
            raise ValueError(f"Unknown benchmark: {benchmark}")

    async def _run_gsm8k_sample(self) -> BenchmarkResult:
        """Simple math reasoning benchmark (built-in sample)."""
        problems = [
            {"question": "If a car travels 60 miles per hour for 2.5 hours, how far does it travel?", "answer": "150"},
            {"question": "A store sells apples for $2 each. If you buy 7 apples and pay with a $20 bill, how much change do you get?", "answer": "6"},
            {"question": "If 3 workers can build a wall in 12 hours, how many hours would it take 6 workers?", "answer": "6"},
            {"question": "A rectangle has a length of 8cm and width of 5cm. What is its area?", "answer": "40"},
            {"question": "If you save $15 per week, how much will you have after 8 weeks?", "answer": "120"},
        ]

        correct = 0
        details = []
        for p in problems:
            response = self._generate(f"Solve this math problem. Give only the numeric answer.\n{p['question']}")
            # Extract number from response
            import re
            numbers = re.findall(r"\d+\.?\d*", response)
            predicted = numbers[-1] if numbers else ""
            is_correct = predicted == p["answer"]
            if is_correct:
                correct += 1
            details.append({
                "question": p["question"],
                "expected": p["answer"],
                "predicted": predicted,
                "correct": is_correct,
            })

        return BenchmarkResult(
            benchmark="gsm8k_sample",
            score=correct / len(problems),
            total=len(problems),
            correct=correct,
            details=details,
        )

    async def _run_code_quality(self) -> BenchmarkResult:
        """Code generation quality benchmark."""
        from foundry.sandbox.executor import SandboxExecutor

        tasks = [
            {"prompt": "Write a Python function that returns the factorial of n.", "test": "assert factorial(5) == 120\nassert factorial(0) == 1"},
            {"prompt": "Write a Python function that checks if a string is a palindrome.", "test": "assert is_palindrome('racecar') == True\nassert is_palindrome('hello') == False"},
            {"prompt": "Write a Python function that returns the nth Fibonacci number.", "test": "assert fibonacci(10) == 55\nassert fibonacci(1) == 1"},
        ]

        sandbox = SandboxExecutor(timeout=10)
        correct = 0
        details = []

        for task in tasks:
            response = self._generate(task["prompt"])
            code = response + "\n" + task["test"]

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                sandbox.execute(code)
            )
            is_correct = result.success
            if is_correct:
                correct += 1
            details.append({
                "prompt": task["prompt"],
                "response": response[:200],
                "correct": is_correct,
                "error": result.stderr[:200] if not is_correct else "",
            })

        sandbox.cleanup()
        return BenchmarkResult(
            benchmark="code_quality",
            score=correct / len(tasks),
            total=len(tasks),
            correct=correct,
            details=details,
        )

    async def _run_tool_use(self) -> BenchmarkResult:
        """Tool use format evaluation."""
        prompts = [
            "Use the python_exec tool to calculate 2**100.",
            "Use the file_write tool to create a file called test.txt with 'hello world'.",
            "Use the shell_exec tool to list files in the current directory.",
        ]

        correct = 0
        details = []
        for prompt in prompts:
            response = self._generate(prompt)
            has_tool = "tool_call" in response.lower() or "python_exec" in response or "file_write" in response or "shell_exec" in response
            if has_tool:
                correct += 1
            details.append({
                "prompt": prompt,
                "has_tool_call": has_tool,
                "response": response[:200],
            })

        return BenchmarkResult(
            benchmark="tool_use",
            score=correct / len(prompts),
            total=len(prompts),
            correct=correct,
            details=details,
        )

    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate a response from the model."""
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            )

        input_len = inputs["input_ids"].shape[1]
        return self.tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
