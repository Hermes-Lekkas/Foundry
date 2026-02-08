# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Security Engine — Main security orchestration."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from foundry.security.audit import SecurityAuditLogger, AuditEvent
from foundry.security.validator import CodeSecurityValidator

logger = logging.getLogger(__name__)

# Try Rust extension
try:
    from foundry_security import SecurityEngine as RustSecurityEngine
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False
    logger.info("Rust security engine not available, using Python fallback")


@dataclass
class SecurityResult:
    """Result of a security check."""
    allowed: bool
    reason: str
    threats_detected: list[str]
    code_hash: str
    execution_time_ms: float


@dataclass
class ExecutionResult:
    """Result of sandboxed execution."""
    success: bool
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_usage_mb: float


class SecurityManager:
    """Main security manager that orchestrates validation and sandboxing."""
    
    def __init__(self, use_rust: bool = True):
        self.audit_logger = SecurityAuditLogger()
        self.validator = CodeSecurityValidator()
        self._rust_engine: Optional[Any] = None
        
        if use_rust and _RUST_AVAILABLE:
            try:
                self._rust_engine = RustSecurityEngine()
                logger.info("Rust security engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Rust engine: {e}")
    
    def validate_and_execute(
        self,
        code: str,
        timeout_ms: int = 30000,
        context: Optional[dict] = None
    ) -> ExecutionResult:
        """Validate code and execute in sandbox."""
        import time
        start = time.time()
        
        # Compute code hash for audit
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        
        # Log attempt
        self.audit_logger.log(AuditEvent(
            event_type="CODE_EXECUTION_ATTEMPT",
            code_hash=code_hash,
            context=context or {}
        ))
        
        # Validate code
        validation = self.validator.validate(code)
        if not validation.is_safe:
            self.audit_logger.log(AuditEvent(
                event_type="CODE_VALIDATION_FAILED",
                code_hash=code_hash,
                details={"threats": validation.threats}
            ))
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Security validation failed: {', '.join(validation.threats)}",
                execution_time_ms=int((time.time() - start) * 1000),
                memory_usage_mb=0.0
            )
        
        # Execute using Rust engine if available
        if self._rust_engine:
            try:
                result = self._rust_engine.execute(code, timeout_ms)
                self.audit_logger.log(AuditEvent(
                    event_type="CODE_EXECUTION_SUCCESS",
                    code_hash=code_hash,
                    details={"rust_engine": True}
                ))
                return ExecutionResult(
                    success=result.success,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    execution_time_ms=result.execution_time_ms,
                    memory_usage_mb=result.memory_usage_mb
                )
            except Exception as e:
                logger.error(f"Rust engine execution failed: {e}")
                # Fall through to Python fallback
        
        # Python fallback - use existing sandbox
        import asyncio
        from foundry.sandbox.executor import SandboxExecutor
        
        sandbox = SandboxExecutor(timeout=timeout_ms // 1000)
        result = asyncio.run(sandbox.execute(code))
        
        self.audit_logger.log(AuditEvent(
            event_type="CODE_EXECUTION_SUCCESS" if result.success else "CODE_EXECUTION_FAILED",
            code_hash=code_hash,
            details={"rust_engine": False, "error_type": result.error_type}
        ))
        
        return ExecutionResult(
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time_ms=int(result.execution_time_ms),
            memory_usage_mb=0.0
        )
    
    def check_security_status(self) -> dict[str, Any]:
        """Check overall security status."""
        status = {
            "rust_engine_available": _RUST_AVAILABLE,
            "rust_engine_active": self._rust_engine is not None,
            "audit_logging_enabled": True,
            "code_validation_enabled": True,
            "recent_events": len(self.audit_logger.get_recent(10)),
        }
        
        if self._rust_engine:
            rust_status = self._rust_engine.security_status()
            status["platform"] = rust_status.platform
            status["sandbox_active"] = rust_status.sandbox_active
        
        return status


class SecureSandbox:
    """High-security sandbox with Rust engine when available."""
    
    def __init__(self):
        self.security_manager = SecurityManager()
    
    async def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """Execute code securely."""
        return self.security_manager.validate_and_execute(code, timeout * 1000)
