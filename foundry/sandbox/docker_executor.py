# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Docker Sandbox — Maximum isolation via containerized execution.

Optional backend for environments where subprocess isolation is insufficient.
Requires Docker to be installed and accessible.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from foundry.sandbox.executor import SandboxResult

logger = logging.getLogger(__name__)

DOCKER_IMAGE = "python:3.11-slim"


class DockerExecutor:
    """Execute code inside a Docker container for maximum isolation."""

    def __init__(
        self,
        timeout: int = 30,
        max_output_bytes: int = 100_000,
        image: str = DOCKER_IMAGE,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
        network_disabled: bool = True,
    ) -> None:
        self.timeout = timeout
        self.max_output_bytes = max_output_bytes
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.network_disabled = network_disabled

    async def is_available(self) -> bool:
        """Check if Docker is accessible."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    async def execute(self, code: str, stdin_data: str = "") -> SandboxResult:
        """Execute Python code inside a Docker container."""
        with tempfile.TemporaryDirectory(prefix="foundry_docker_") as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            cmd = [
                "docker", "run",
                "--rm",
                "--memory", self.memory_limit,
                f"--cpus={self.cpu_limit}",
                "--read-only",
                "--tmpfs", "/tmp:size=64m",
                "-v", f"{tmpdir}:/sandbox:ro",
                "-w", "/sandbox",
            ]

            if self.network_disabled:
                cmd.append("--network=none")

            cmd.extend([self.image, "python", "/sandbox/script.py"])

            start = time.monotonic()

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(input=stdin_data.encode() if stdin_data else None),
                        timeout=self.timeout,
                    )
                except asyncio.TimeoutError:
                    # Kill the container
                    proc.kill()
                    await proc.wait()
                    elapsed = (time.monotonic() - start) * 1000
                    return SandboxResult(
                        success=False,
                        stderr=f"Docker execution timed out after {self.timeout}s",
                        execution_time_ms=elapsed,
                        timed_out=True,
                        error_type="TimeoutError",
                    )

                elapsed = (time.monotonic() - start) * 1000
                stdout = stdout_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")
                stderr = stderr_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")

                return SandboxResult(
                    success=proc.returncode == 0,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time_ms=elapsed,
                )

            except FileNotFoundError:
                return SandboxResult(
                    success=False,
                    stderr="Docker is not installed or not in PATH",
                    error_type="FileNotFoundError",
                )
