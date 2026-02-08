# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Tests for the Sandbox Executor — subprocess isolation."""

import asyncio
import pytest
from foundry.sandbox.executor import SandboxExecutor, SandboxResult


@pytest.fixture
def sandbox():
    s = SandboxExecutor(timeout=10)
    yield s
    s.cleanup()


@pytest.mark.asyncio
async def test_simple_execution(sandbox):
    result = await sandbox.execute("print('hello foundry')")
    assert result.success
    assert "hello foundry" in result.stdout


@pytest.mark.asyncio
async def test_math_execution(sandbox):
    result = await sandbox.execute("print(2 ** 10)")
    assert result.success
    assert "1024" in result.stdout


@pytest.mark.asyncio
async def test_syntax_error(sandbox):
    result = await sandbox.execute("def foo(")
    assert not result.success
    assert "SyntaxError" in result.stderr or result.error_type == "SyntaxError"


@pytest.mark.asyncio
async def test_runtime_error(sandbox):
    result = await sandbox.execute("1/0")
    assert not result.success
    assert "ZeroDivision" in result.stderr or "ZeroDivision" in result.error_type


@pytest.mark.asyncio
async def test_timeout(sandbox):
    sandbox.timeout = 2
    result = await sandbox.execute("import time; time.sleep(10)")
    assert not result.success
    assert result.timed_out


@pytest.mark.asyncio
async def test_restricted_imports(sandbox):
    result = await sandbox.execute("import socket")
    assert not result.success
    assert "restricted" in result.stderr.lower() or "import" in result.stderr.lower()


@pytest.mark.asyncio
async def test_safe_imports_allowed(sandbox):
    result = await sandbox.execute("import json; print(json.dumps({'ok': True}))")
    assert result.success
    assert '{"ok": true}' in result.stdout


@pytest.mark.asyncio
async def test_execution_time_tracked(sandbox):
    result = await sandbox.execute("print('fast')")
    assert result.execution_time_ms > 0
    assert result.execution_time_ms < 10000  # Should be under 10s


@pytest.mark.asyncio
async def test_multiline_code(sandbox):
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
"""
    result = await sandbox.execute(code)
    assert result.success
    assert "55" in result.stdout


@pytest.mark.asyncio
async def test_result_summary(sandbox):
    result = await sandbox.execute("print('test')")
    summary = result.summary()
    assert "OK" in summary
