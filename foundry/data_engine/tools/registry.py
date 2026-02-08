# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tool Registry — Defines and manages executable tools for trajectory synthesis.

Each tool maps to a sandboxed execution path via the ToolExecutor.
Tool schemas are defined in JSON Schema for function calling format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    """A tool available for agentic trajectory synthesis."""

    name: str
    description: str
    parameters: dict[str, Any]
    category: str = "general"
    risk_level: str = "low"  # low | medium | high

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


# ── Built-in tool definitions ────────────────────────────────────────────────

BUILTIN_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="python_exec",
        description="Execute Python code and return stdout/stderr. Use for computation, data processing, and analysis.",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
            },
            "required": ["code"],
        },
        category="execution",
        risk_level="medium",
    ),
    ToolDefinition(
        name="file_read",
        description="Read the contents of a file from the workspace.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                },
            },
            "required": ["path"],
        },
        category="file_io",
        risk_level="low",
    ),
    ToolDefinition(
        name="file_write",
        description="Write content to a file in the workspace. Creates parent directories if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
        category="file_io",
        risk_level="low",
    ),
    ToolDefinition(
        name="shell_exec",
        description="Execute a shell command and return output. Use for system operations, listing files, etc.",
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
            },
            "required": ["command"],
        },
        category="execution",
        risk_level="medium",
    ),
]


class ToolRegistry:
    """Registry of available tools for trajectory synthesis."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        for tool in BUILTIN_TOOLS:
            self.register(tool)

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolDefinition]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def to_schemas(self) -> list[dict[str, Any]]:
        return [t.to_schema() for t in self._tools.values()]
