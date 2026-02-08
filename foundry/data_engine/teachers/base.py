# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Base Teacher — Abstract interface for data synthesis models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """A chat message."""

    role: str  # system | user | assistant | tool
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class TeacherResponse:
    """Response from a Teacher model."""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class Teacher(ABC):
    """Abstract Teacher model for data synthesis."""

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> TeacherResponse:
        """Generate a response from the teacher model."""
        ...

    @abstractmethod
    async def critique(
        self,
        response: str,
        principle: str,
        template: str,
    ) -> str:
        """Generate a critique of a response against a principle."""
        ...

    @abstractmethod
    async def revise(
        self,
        response: str,
        critique: str,
        template: str,
    ) -> str:
        """Revise a response based on critique."""
        ...

    async def generate_preference_pair(
        self,
        prompt: str,
        principle: str,
    ) -> tuple[str, str]:
        """Generate a (chosen, rejected) pair for DPO training.

        Default: generate two responses, use critique to rank them.
        """
        # Generate two responses at higher temperature
        r1 = await self.generate(
            [Message(role="user", content=prompt)], temperature=0.9
        )
        r2 = await self.generate(
            [Message(role="user", content=prompt)], temperature=0.9
        )

        # Critique both
        c1 = await self.critique(r1.content, principle, "Rate 1-10: {{ response }}")
        c2 = await self.critique(r2.content, principle, "Rate 1-10: {{ response }}")

        # Simple heuristic: longer critique = more issues = worse
        if len(c1) <= len(c2):
            return r1.content, r2.content  # r1 is chosen
        return r2.content, r1.content  # r2 is chosen
