//! Audit Module
//! 
//! Comprehensive security logging and audit trail.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

/// Security event types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event_type")]
pub enum SecurityEvent {
    CodeExecution {
        code_hash: String,
        timestamp: DateTime<Utc>,
    },
    ThreatDetected {
        threat_type: String,
        action: String,
    },
    PolicyViolation {
        policy: String,
        details: String,
    },
    ResourceLimitExceeded {
        resource: String,
        limit: u64,
        actual: u64,
    },
    SandboxEscapeAttempt {
        method: String,
        blocked: bool,
    },
    AuthenticationEvent {
        success: bool,
        identity: String,
    },
    ConfigurationChange {
        setting: String,
        old_value: String,
        new_value: String,
    },
}

/// Audit logger
pub struct AuditLogger {
    events: Mutex<Vec<SecurityEvent>>,
    max_events: usize,
}

impl AuditLogger {
    /// Create a new audit logger
    pub fn new() -> Self {
        Self {
            events: Mutex::new(Vec::new()),
            max_events: 10000,
        }
    }
    
    /// Log a security event
    pub fn log(&self, event: SecurityEvent) {
        let mut events = self.events.lock().unwrap();
        events.push(event);
        
        // Keep only recent events
        if events.len() > self.max_events {
            events.remove(0);
        }
    }
    
    /// Get recent events
    pub fn get_recent(&self, limit: usize) -> Vec<SecurityEvent> {
        let events = self.events.lock().unwrap();
        events.iter().rev().take(limit).cloned().collect()
    }
    
    /// Get all events
    pub fn get_all(&self) -> Vec<SecurityEvent> {
        let events = self.events.lock().unwrap();
        events.clone()
    }
    
    /// Export to JSON
    pub fn export_json(&self) -> String {
        let events = self.events.lock().unwrap();
        serde_json::to_string_pretty(&*events).unwrap_or_default()
    }
    
    /// Get event count
    pub fn event_count(&self) -> usize {
        let events = self.events.lock().unwrap();
        events.len()
    }
    
    /// Clear all events
    pub fn clear(&self) {
        let mut events = self.events.lock().unwrap();
        events.clear();
    }
}

impl Default for AuditLogger {
    fn default() -> Self {
        Self::new()
    }
}
