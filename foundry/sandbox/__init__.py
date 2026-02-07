# THE FOUNDRY — PROPRIETARY SOFTWARE LICENSE
# Copyright (c) 2026 Hermes Lekkas. All rights reserved.
#
# This software is provided under a proprietary license.
# See the LICENSE file for details.

"""Sandbox — Secure execution environment for tool calls and code evaluation.

Shared by both the Data Engine (verifiable trajectory synthesis) and the
Evaluator (RLVR reward computation). Supports subprocess and Docker backends.
"""

from foundry.sandbox.executor import SandboxExecutor, SandboxResult
from foundry.sandbox.tool_executor import ToolExecutor, ToolResult
from foundry.sandbox.validators import OutputValidator

__all__ = [
    "SandboxExecutor",
    "SandboxResult",
    "ToolExecutor",
    "ToolResult",
    "OutputValidator",
]
