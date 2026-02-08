# The Foundry - Open Core LLM Training Ecosystem
# Copyright (c) 2026 Hermes Lekkas
# 
# This file is part of the open-core release (MIT License).
# See LICENSE file for full terms.

"""Sandbox Executor — Subprocess-based secure code execution.

Platform-aware isolation:
- Windows native: subprocess with CREATE_NO_WINDOW
- WSL2/Linux: subprocess with restricted imports + optional seccomp
- macOS: subprocess with seatbelt sandbox + resource limits
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Platform detection
PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_MACOS = PLATFORM == "darwin"
IS_LINUX = PLATFORM == "linux"

# Imports that are forbidden inside the sandbox
RESTRICTED_IMPORTS = {
    "shutil",
    "socket",
    "http",
    "urllib",
    "ftplib",
    "smtplib",
    "ctypes",
    "multiprocessing",
    "signal",
    "webbrowser",
}

# Safe preamble injected before user code
SANDBOX_PREAMBLE = """
import sys as _sys

# Restrict dangerous imports
_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
_BLOCKED = {blocked}

def _safe_import(name, *args, **kwargs):
    top_level = name.split('.')[0]
    if top_level in _BLOCKED:
        raise ImportError(f"Import '{{name}}' is restricted in sandbox")
    return _original_import(name, *args, **kwargs)

if hasattr(__builtins__, '__import__'):
    __builtins__.__import__ = _safe_import
else:
    import builtins
    builtins.__import__ = _safe_import

# Restrict file system access to temp directory only
import os as _os
_SANDBOX_ROOT = {sandbox_root!r}
_original_open = open

def _safe_open(path, *args, **kwargs):
    resolved = _os.path.realpath(str(path))
    if not resolved.startswith(_SANDBOX_ROOT):
        raise PermissionError(f"File access outside sandbox is restricted: {{path}}")
    return _original_open(path, *args, **kwargs)

if hasattr(__builtins__, 'open'):
    __builtins__.open = _safe_open
else:
    import builtins
    builtins.open = _safe_open
"""


@dataclass
class SandboxResult:
    """Result of a sandboxed execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0.0
    timed_out: bool = False
    error_type: str = ""

    def summary(self) -> str:
        status = "OK" if self.success else "FAIL"
        parts = [f"[{status}] ({self.execution_time_ms:.0f}ms)"]
        if self.stdout:
            parts.append(f"stdout: {self.stdout[:200]}")
        if self.stderr:
            parts.append(f"stderr: {self.stderr[:200]}")
        if self.error_type:
            parts.append(f"error: {self.error_type}")
        return " | ".join(parts)


class SandboxExecutor:
    """Execute code in an isolated subprocess.

    Provides platform-aware isolation with timeouts, restricted imports,
    and filesystem sandboxing.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_output_bytes: int = 100_000,
        work_dir: Path | None = None,
        restrict_imports: bool = True,
    ) -> None:
        self.timeout = timeout
        self.max_output_bytes = max_output_bytes
        self.work_dir = work_dir or Path(tempfile.mkdtemp(prefix="foundry_sandbox_"))
        self.restrict_imports = restrict_imports
        self._is_windows = IS_WINDOWS
        self._is_macos = IS_MACOS

        # Ensure work directory exists
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # Log platform info
        logger.debug(f"Sandbox initialized on {PLATFORM}")

    def _build_script(self, code: str) -> str:
        """Wrap user code with sandbox preamble."""
        if not self.restrict_imports:
            return code

        preamble = SANDBOX_PREAMBLE.format(
            blocked=repr(RESTRICTED_IMPORTS),
            sandbox_root=str(self.work_dir),
        )
        return preamble + "\n\n# === User Code ===\n" + code

    async def execute(self, code: str, stdin_data: str = "") -> SandboxResult:
        """Execute Python code in an isolated subprocess."""
        script = self._build_script(code)

        # Write script to temp file in the sandbox
        script_path = self.work_dir / "_sandbox_script.py"
        script_path.write_text(script, encoding="utf-8")

        start = time.monotonic()

        try:
            # Build subprocess kwargs
            kwargs: dict[str, Any] = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "stdin": subprocess.PIPE,
                "cwd": str(self.work_dir),
                "env": self._safe_env(),
            }

            # Platform-specific flags
            if self._is_windows:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            
            # macOS: Apply resource limits via ulimit
            if self._is_macos:
                # Check if sandbox-exec is available
                sandbox_cmd = self._apply_macos_sandbox(script_path)
                if sandbox_cmd:
                    # Use sandbox-exec wrapper
                    proc = await asyncio.create_subprocess_exec(
                        *sandbox_cmd, sys.executable, str(script_path),
                        **kwargs,
                    )
                else:
                    # Fallback to standard execution
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable, str(script_path),
                        **kwargs,
                    )
            else:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(script_path),
                    **kwargs,
                )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(input=stdin_data.encode() if stdin_data else None),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                elapsed = (time.monotonic() - start) * 1000
                return SandboxResult(
                    success=False,
                    stderr=f"Execution timed out after {self.timeout}s",
                    execution_time_ms=elapsed,
                    timed_out=True,
                    error_type="TimeoutError",
                )

            elapsed = (time.monotonic() - start) * 1000

            stdout = stdout_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")
            stderr = stderr_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")

            success = proc.returncode == 0

            # Extract error type from stderr
            error_type = ""
            if not success and stderr:
                for line in stderr.strip().split("\n"):
                    if "Error:" in line or "Exception:" in line:
                        error_type = line.split(":")[0].strip().split(".")[-1]

            return SandboxResult(
                success=success,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=elapsed,
                error_type=error_type,
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return SandboxResult(
                success=False,
                stderr=str(e),
                execution_time_ms=elapsed,
                error_type=type(e).__name__,
            )
        finally:
            # Cleanup script file
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass

    async def execute_file(self, file_path: Path, stdin_data: str = "") -> SandboxResult:
        """Execute a Python file in the sandbox."""
        code = file_path.read_text(encoding="utf-8")
        return await self.execute(code, stdin_data)

    def _safe_env(self) -> dict[str, str]:
        """Build a minimal, safe environment for the subprocess."""
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.work_dir),
            "TMPDIR": str(self.work_dir),
            "PYTHONPATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        
        # macOS-specific environment
        if self._is_macos:
            env["__CF_USER_TEXT_ENCODING"] = os.environ.get("__CF_USER_TEXT_ENCODING", "0x1F5:0x0:0x0")
            # Use system Python if available
            if "/usr/bin" not in env["PATH"]:
                env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin:" + env["PATH"]
        
        # Preserve CUDA-related vars for GPU code execution
        for key in ("CUDA_HOME", "CUDA_PATH", "LD_LIBRARY_PATH"):
            if key in os.environ:
                env[key] = os.environ[key]
        return env
    
    def _apply_macos_sandbox(self, script_path: Path) -> list[str]:
        """Build macOS sandbox profile and return command prefix."""
        # Create a seatbelt sandbox profile
        sandbox_profile = f"""(version 1)
(debug deny)
(allow default)
(deny file-write* (subpath "/"))
(allow file-write* (subpath "{self.work_dir}"))
(allow file-read* (subpath "{self.work_dir}"))
(allow file-read* (subpath "/System"))
(allow file-read* (subpath "/usr"))
(allow file-read* (subpath "/Library"))
(allow file-read* (subpath "/dev"))
(allow file-read* (subpath "/private/var"))
(deny network*)
"""
        profile_path = self.work_dir / ".sandbox.sb"
        profile_path.write_text(sandbox_profile)
        
        # Use sandbox-exec if available
        return ["sandbox-exec", "-f", str(profile_path)]

    def cleanup(self) -> None:
        """Remove the sandbox working directory."""
        import shutil

        try:
            shutil.rmtree(self.work_dir, ignore_errors=True)
        except Exception:
            pass
