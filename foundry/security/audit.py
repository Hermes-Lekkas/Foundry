# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Security Audit Logger — Immutable security event log."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class AuditEvent:
    """Security audit event."""
    event_type: str
    timestamp: float = 0.0
    code_hash: str = ""
    user_id: str = ""
    session_id: str = ""
    details: dict = None
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.details is None:
            self.details = {}
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "timestamp_human": datetime.fromtimestamp(self.timestamp).isoformat(),
            "code_hash": self.code_hash,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "details": self.details,
        }


class SecurityAuditLogger:
    """
    Immutable audit logger for security events.
    
    All security-relevant events are logged to an append-only SQLite database
    with integrity verification.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path("./.foundry/security_audit.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection
    
    def _init_db(self) -> None:
        """Initialize the audit database."""
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                code_hash TEXT,
                user_id TEXT,
                session_id TEXT,
                details TEXT,
                integrity_hash TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_code_hash ON audit_events(code_hash)
        """)
        conn.commit()
    
    def log(self, event: AuditEvent) -> None:
        """Log a security event."""
        conn = self._get_connection()
        
        # Compute integrity hash (chain of events)
        prev_hash = self._get_last_hash(conn)
        data = f"{prev_hash}:{event.timestamp}:{event.event_type}:{event.code_hash}"
        import hashlib
        integrity_hash = hashlib.sha256(data.encode()).hexdigest()[:32]
        
        conn.execute(
            """
            INSERT INTO audit_events 
            (timestamp, event_type, code_hash, user_id, session_id, details, integrity_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.timestamp,
                event.event_type,
                event.code_hash,
                event.user_id,
                event.session_id,
                json.dumps(event.details),
                integrity_hash
            )
        )
        conn.commit()
    
    def _get_last_hash(self, conn: sqlite3.Connection) -> str:
        """Get the integrity hash of the last event."""
        cursor = conn.execute(
            "SELECT integrity_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else "0" * 32
    
    def get_recent(self, limit: int = 100) -> list[AuditEvent]:
        """Get recent audit events."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT timestamp, event_type, code_hash, user_id, session_id, details
            FROM audit_events
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        events = []
        for row in cursor.fetchall():
            events.append(AuditEvent(
                timestamp=row[0],
                event_type=row[1],
                code_hash=row[2] or "",
                user_id=row[3] or "",
                session_id=row[4] or "",
                details=json.loads(row[5]) if row[5] else {}
            ))
        return events
    
    def get_by_code_hash(self, code_hash: str) -> list[AuditEvent]:
        """Get all events for a specific code hash."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT timestamp, event_type, code_hash, user_id, session_id, details
            FROM audit_events
            WHERE code_hash = ?
            ORDER BY timestamp DESC
            """,
            (code_hash,)
        )
        
        events = []
        for row in cursor.fetchall():
            events.append(AuditEvent(
                timestamp=row[0],
                event_type=row[1],
                code_hash=row[2] or "",
                user_id=row[3] or "",
                session_id=row[4] or "",
                details=json.loads(row[5]) if row[5] else {}
            ))
        return events
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of the audit log."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT id, timestamp, event_type, code_hash, integrity_hash FROM audit_events ORDER BY id"
        )
        
        prev_hash = "0" * 32
        for row in cursor.fetchall():
            stored_hash = row[4]
            data = f"{prev_hash}:{row[1]}:{row[2]}:{row[3]}"
            import hashlib
            computed_hash = hashlib.sha256(data.encode()).hexdigest()[:32]
            
            if stored_hash != computed_hash:
                return False
            
            prev_hash = stored_hash
        
        return True
    
    def export_to_json(self, output_path: Path) -> None:
        """Export audit log to JSON."""
        events = self.get_recent(10000)
        data = {
            "exported_at": datetime.now().isoformat(),
            "event_count": len(events),
            "events": [e.to_dict() for e in events]
        }
        output_path.write_text(json.dumps(data, indent=2))
    
    def get_statistics(self) -> dict[str, Any]:
        """Get audit statistics."""
        conn = self._get_connection()
        
        stats = {}
        
        # Total events
        cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
        stats["total_events"] = cursor.fetchone()[0]
        
        # Events by type
        cursor = conn.execute(
            "SELECT event_type, COUNT(*) FROM audit_events GROUP BY event_type"
        )
        stats["events_by_type"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Time range
        cursor = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM audit_events"
        )
        row = cursor.fetchone()
        if row and row[0]:
            stats["first_event"] = datetime.fromtimestamp(row[0]).isoformat()
            stats["last_event"] = datetime.fromtimestamp(row[1]).isoformat()
        
        # Integrity status
        stats["integrity_verified"] = self.verify_integrity()
        
        return stats
