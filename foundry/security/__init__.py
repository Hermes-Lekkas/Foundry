# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Security Module — High-performance security engine integration."""

from foundry.security.engine import SecurityManager, SecureSandbox
from foundry.security.audit import SecurityAuditLogger, AuditEvent
from foundry.security.validator import CodeSecurityValidator

__all__ = [
    "SecurityManager",
    "SecureSandbox",
    "SecurityAuditLogger",
    "AuditEvent",
    "CodeSecurityValidator",
]

# Try to import Rust extension
try:
    from foundry_security import SecurityEngine, PyExecutionResult, PySecurityStatus
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False
