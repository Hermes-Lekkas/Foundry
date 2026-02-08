# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for the Tool Executor — sandboxed tool calls."""

import pytest
from foundry.sandbox.tool_executor import ToolExecutor


@pytest.fixture
def tool_exec():
    te = ToolExecutor()
    yield te
    te.cleanup()


@pytest.mark.asyncio
async def test_python_exec(tool_exec):
    result = await tool_exec.execute("python_exec", {"code": "print(42)"})
    assert result.success
    assert "42" in result.output


@pytest.mark.asyncio
async def test_file_write_and_read(tool_exec):
    # Write
    write_result = await tool_exec.execute("file_write", {
        "path": "test_file.txt",
        "content": "hello from foundry",
    })
    assert write_result.success

    # Read
    read_result = await tool_exec.execute("file_read", {"path": "test_file.txt"})
    assert read_result.success
    assert "hello from foundry" in read_result.output


@pytest.mark.asyncio
async def test_file_read_nonexistent(tool_exec):
    result = await tool_exec.execute("file_read", {"path": "nonexistent.txt"})
    assert not result.success
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_path_traversal_blocked(tool_exec):
    result = await tool_exec.execute("file_read", {"path": "../../../etc/passwd"})
    assert not result.success
    assert "traversal" in result.error.lower() or "denied" in result.error.lower()


@pytest.mark.asyncio
async def test_unknown_tool(tool_exec):
    result = await tool_exec.execute("nonexistent_tool", {})
    assert not result.success
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_available_tools_schema(tool_exec):
    tools = tool_exec.available_tools
    assert len(tools) >= 4  # python_exec, file_read, file_write, shell_exec
    names = [t["name"] for t in tools]
    assert "python_exec" in names
    assert "file_read" in names
    assert "file_write" in names


@pytest.mark.asyncio
async def test_tool_result_feedback(tool_exec):
    result = await tool_exec.execute("python_exec", {"code": "print('ok')"})
    feedback = result.to_feedback()
    assert "python_exec" in feedback
    assert "Success" in feedback


@pytest.mark.asyncio
async def test_tool_result_dict(tool_exec):
    result = await tool_exec.execute("python_exec", {"code": "print(1)"})
    d = result.to_dict()
    assert d["tool_name"] == "python_exec"
    assert d["success"] is True
    assert "execution_time_ms" in d
