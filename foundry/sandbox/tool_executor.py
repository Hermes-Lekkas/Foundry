# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tool Executor — Executes real tool calls during trajectory synthesis.

Wraps file I/O, HTTP requests, Python execution, and shell commands
in sandboxed environments. This is what makes trajectories *verifiable* —
we execute real tool calls and feed real results back to the Teacher.
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from foundry.sandbox.executor import SandboxExecutor, SandboxResult

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of a tool execution."""

    tool_name: str
    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_feedback(self) -> str:
        """Format as feedback string for the Teacher model."""
        if self.success:
            return f"[Tool: {self.tool_name}] Success.\n{self.output}"
        else:
            return f"[Tool: {self.tool_name}] Failed.\nError: {self.error}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class ToolExecutor:
    """Executes tool calls in sandboxed environments.

    Supports:
    - python_exec: Execute Python code
    - file_read: Read a file from the sandbox workspace
    - file_write: Write a file in the sandbox workspace
    - shell_exec: Execute a shell command
    - http_get: Perform an HTTP GET (disabled by default)
    """

    def __init__(
        self,
        sandbox: SandboxExecutor | None = None,
        work_dir: Path | None = None,
        allow_network: bool = False,
    ) -> None:
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="foundry_tools_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox = sandbox or SandboxExecutor(work_dir=self.work_dir)
        self.allow_network = allow_network

        self._tools: dict[str, Any] = {
            "python_exec": self._exec_python,
            "file_read": self._exec_file_read,
            "file_write": self._exec_file_write,
            "shell_exec": self._exec_shell,
            "http_get": self._exec_http_get,
        }

    @property
    def available_tools(self) -> list[dict[str, Any]]:
        """Return JSON Schema definitions of available tools."""
        tools = [
            {
                "name": "python_exec",
                "description": "Execute Python code and return the output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                    },
                    "required": ["code"],
                },
            },
            {
                "name": "file_read",
                "description": "Read the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "file_write",
                "description": "Write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to write"},
                        "content": {"type": "string", "description": "Content to write"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "shell_exec",
                "description": "Execute a shell command and return output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run"},
                    },
                    "required": ["command"],
                },
            },
        ]
        if self.allow_network:
            tools.append({
                "name": "http_get",
                "description": "Perform an HTTP GET request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                    },
                    "required": ["url"],
                },
            })
        return tools

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool call with the given arguments."""
        handler = self._tools.get(tool_name)
        if handler is None:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}. Available: {list(self._tools.keys())}",
            )

        try:
            return await handler(arguments)
        except Exception as e:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

    async def _exec_python(self, args: dict[str, Any]) -> ToolResult:
        """Execute Python code in the sandbox."""
        code = args.get("code", "")
        result = await self.sandbox.execute(code)
        return ToolResult(
            tool_name="python_exec",
            success=result.success,
            output=result.stdout,
            error=result.stderr if not result.success else "",
            execution_time_ms=result.execution_time_ms,
        )

    async def _exec_file_read(self, args: dict[str, Any]) -> ToolResult:
        """Read a file from the workspace."""
        path = args.get("path", "")
        target = (self.work_dir / path).resolve()

        # Security: ensure path is within workspace
        try:
            target.relative_to(self.work_dir.resolve())
        except ValueError:
            return ToolResult(
                tool_name="file_read",
                success=False,
                error="Path traversal detected: access denied",
            )

        if not target.exists():
            return ToolResult(
                tool_name="file_read",
                success=False,
                error=f"File not found: {path}",
            )

        try:
            content = target.read_text(encoding="utf-8")
            return ToolResult(
                tool_name="file_read",
                success=True,
                output=content,
            )
        except Exception as e:
            return ToolResult(
                tool_name="file_read",
                success=False,
                error=str(e),
            )

    async def _exec_file_write(self, args: dict[str, Any]) -> ToolResult:
        """Write a file to the workspace."""
        path = args.get("path", "")
        content = args.get("content", "")
        target = (self.work_dir / path).resolve()

        # Security: ensure path is within workspace
        try:
            target.relative_to(self.work_dir.resolve())
        except ValueError:
            return ToolResult(
                tool_name="file_write",
                success=False,
                error="Path traversal detected: access denied",
            )

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(
                tool_name="file_write",
                success=True,
                output=f"Written {len(content)} bytes to {path}",
            )
        except Exception as e:
            return ToolResult(
                tool_name="file_write",
                success=False,
                error=str(e),
            )

    async def _exec_shell(self, args: dict[str, Any]) -> ToolResult:
        """Execute a shell command in the sandbox."""
        command = args.get("command", "")
        # Wrap shell command as Python subprocess call for sandboxing
        code = f"""
import subprocess
result = subprocess.run(
    {command!r},
    shell=True,
    capture_output=True,
    text=True,
    timeout=15,
    cwd={str(self.work_dir)!r},
)
print(result.stdout, end='')
if result.stderr:
    import sys
    print(result.stderr, end='', file=sys.stderr)
if result.returncode != 0:
    import sys
    sys.exit(result.returncode)
"""
        result = await self.sandbox.execute(code)
        return ToolResult(
            tool_name="shell_exec",
            success=result.success,
            output=result.stdout,
            error=result.stderr if not result.success else "",
            execution_time_ms=result.execution_time_ms,
        )

    async def _exec_http_get(self, args: dict[str, Any]) -> ToolResult:
        """Perform an HTTP GET request (when network is allowed)."""
        if not self.allow_network:
            return ToolResult(
                tool_name="http_get",
                success=False,
                error="Network access is disabled in this sandbox",
            )

        url = args.get("url", "")
        code = f"""
import urllib.request
try:
    with urllib.request.urlopen({url!r}, timeout=10) as response:
        data = response.read().decode('utf-8', errors='replace')[:10000]
        print(data)
except Exception as e:
    import sys
    print(str(e), file=sys.stderr)
    sys.exit(1)
"""
        # Use unrestricted sandbox for network access
        unrestricted = SandboxExecutor(
            work_dir=self.work_dir,
            restrict_imports=False,
            timeout=15,
        )
        result = await unrestricted.execute(code)
        return ToolResult(
            tool_name="http_get",
            success=result.success,
            output=result.stdout,
            error=result.stderr if not result.success else "",
            execution_time_ms=result.execution_time_ms,
        )

    def cleanup(self) -> None:
        """Clean up the workspace."""
        self.sandbox.cleanup()
