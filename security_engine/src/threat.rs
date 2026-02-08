//! Threat Detection Module
//! 
//! Runtime threat detection and behavioral analysis.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Threat level
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThreatLevel {
    Low,
    Medium,
    High,
    Critical,
}

/// Threat indicator
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatIndicator {
    pub id: String,
    pub name: String,
    pub description: String,
    pub level: ThreatLevel,
    pub pattern: String,
}

/// Threat detection result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThreatResult {
    pub detected: bool,
    pub indicators: Vec<ThreatIndicator>,
    pub confidence: f64,
    pub recommendation: String,
}

/// Behavioral analyzer
pub struct BehavioralAnalyzer {
    indicators: Vec<ThreatIndicator>,
    baseline: HashMap<String, f64>,
}

impl BehavioralAnalyzer {
    /// Create a new behavioral analyzer
    pub fn new() -> Self {
        let indicators = vec![
            ThreatIndicator {
                id: "THREAT-001".to_string(),
                name: "Rapid File Access".to_string(),
                description: "Unusually high rate of file system access".to_string(),
                level: ThreatLevel::Medium,
                pattern: "file_access_rate".to_string(),
            },
            ThreatIndicator {
                id: "THREAT-002".to_string(),
                name: "Network Activity".to_string(),
                description: "Attempted network connection from sandbox".to_string(),
                level: ThreatLevel::High,
                pattern: "network_activity".to_string(),
            },
            ThreatIndicator {
                id: "THREAT-003".to_string(),
                name: "Process Spawning".to_string(),
                description: "Attempting to spawn child processes".to_string(),
                level: ThreatLevel::Medium,
                pattern: "process_spawn".to_string(),
            },
            ThreatIndicator {
                id: "THREAT-004".to_string(),
                name: "Memory Exhaustion".to_string(),
                description: "Attempting to exhaust system memory".to_string(),
                level: ThreatLevel::High,
                pattern: "memory_exhaustion".to_string(),
            },
            ThreatIndicator {
                id: "THREAT-005".to_string(),
                name: "Path Traversal".to_string(),
                description: "Attempting to access files outside sandbox".to_string(),
                level: ThreatLevel::Critical,
                pattern: "path_traversal".to_string(),
            },
            ThreatIndicator {
                id: "THREAT-006".to_string(),
                name: "Environment Variable Access".to_string(),
                description: "Attempting to read sensitive env vars".to_string(),
                level: ThreatLevel::Low,
                pattern: "env_access".to_string(),
            },
        ];
        
        Self {
            indicators,
            baseline: HashMap::new(),
        }
    }
    
    /// Analyze execution metrics for threats
    pub fn analyze(
        &self,
        metrics: &ExecutionMetrics
    ) -> ThreatResult {
        let mut detected_indicators = Vec::new();
        let mut confidence_sum = 0.0;
        
        // Check for path traversal
        if self.detect_path_traversal(metrics) {
            if let Some(indicator) = self.indicators.iter().find(|i| i.id == "THREAT-005") {
                detected_indicators.push(indicator.clone());
                confidence_sum += 0.95;
            }
        }
        
        // Check for memory exhaustion attempt
        if metrics.memory_mb > 1000 {
            if let Some(indicator) = self.indicators.iter().find(|i| i.id == "THREAT-004") {
                detected_indicators.push(indicator.clone());
                confidence_sum += 0.8;
            }
        }
        
        // Check for rapid file access
        if metrics.file_operations > 100 {
            if let Some(indicator) = self.indicators.iter().find(|i| i.id == "THREAT-001") {
                detected_indicators.push(indicator.clone());
                confidence_sum += 0.6;
            }
        }
        
        let detected = !detected_indicators.is_empty();
        let confidence = if detected {
            confidence_sum / detected_indicators.len() as f64
        } else {
            0.0
        };
        
        let recommendation = if detected {
            format!(
                "Threats detected: {}. Immediate action recommended.",
                detected_indicators.iter()
                    .map(|i| i.name.clone())
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        } else {
            "No threats detected.".to_string()
        };
        
        ThreatResult {
            detected,
            indicators: detected_indicators,
            confidence,
            recommendation,
        }
    }
    
    /// Detect path traversal attempts
    fn detect_path_traversal(&self, metrics: &ExecutionMetrics) -> bool {
        // Check for suspicious paths in file operations
        let suspicious_patterns = ["../", "..\\", "/etc/", "/proc/", "C:\\"];
        
        for pattern in &suspicious_patterns {
            if metrics.file_paths_accessed.iter().any(|p| p.contains(pattern)) {
                return true;
            }
        }
        
        false
    }
    
    /// Update baseline from normal executions
    pub fn update_baseline(&mut self, metrics: &ExecutionMetrics) {
        self.baseline.insert(
            "avg_memory".to_string(),
            metrics.memory_mb
        );
        self.baseline.insert(
            "avg_file_ops".to_string(),
            metrics.file_operations as f64
        );
    }
}

impl Default for BehavioralAnalyzer {
    fn default() -> Self {
        Self::new()
    }
}

/// Execution metrics for analysis
#[derive(Debug, Clone, Default)]
pub struct ExecutionMetrics {
    pub execution_time_ms: u64,
    pub memory_mb: f64,
    pub cpu_percent: f64,
    pub file_operations: u32,
    pub file_paths_accessed: Vec<String>,
    pub network_requests: u32,
    pub processes_spawned: u32,
    pub syscalls_made: u32,
}
