//! Foundry Security Engine
//! 
//! High-performance security system for sandboxing and monitoring
//! AI training code execution. Written in Rust for memory safety
//! and performance.

use pyo3::prelude::*;

pub mod sandbox;
pub mod audit;
pub mod validator;
pub mod threat;

use sandbox::{Sandbox, SandboxConfig};
use audit::{AuditLogger, SecurityEvent};
use validator::CodeValidator;

/// Python-facing security engine
#[pyclass]
pub struct SecurityEngine {
    sandbox: Sandbox,
    audit_logger: AuditLogger,
    validator: CodeValidator,
}

#[pymethods]
impl SecurityEngine {
    /// Create a new security engine with default configuration
    #[new]
    fn new() -> PyResult<Self> {
        let sandbox = Sandbox::new(SandboxConfig::default())
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        let audit_logger = AuditLogger::new();
        let validator = CodeValidator::new();
        
        Ok(Self {
            sandbox,
            audit_logger,
            validator,
        })
    }
    
    /// Execute code in a sandboxed environment
    fn execute(&self, code: &str, timeout_ms: u64) -> PyResult<PyExecutionResult> {
        // Log the execution attempt
        self.audit_logger.log(SecurityEvent::CodeExecution {
            code_hash: sha256(code),
            timestamp: chrono::Utc::now(),
        });
        
        // Validate code before execution
        let validation = self.validator.validate_python(code)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        
        if !validation.is_safe {
            self.audit_logger.log(SecurityEvent::ThreatDetected {
                threat_type: validation.threats.join(", "),
                action: "blocked".to_string(),
            });
            
            return Err(pyo3::exceptions::PyPermissionError::new_err(
                format!("Code validation failed: {}", validation.threats.join(", "))
            ));
        }
        
        // Execute in sandbox
        let result = self.sandbox.execute(code, timeout_ms)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        Ok(PyExecutionResult {
            success: result.success,
            stdout: result.stdout,
            stderr: result.stderr,
            execution_time_ms: result.execution_time_ms,
            memory_usage_mb: result.memory_usage_mb,
        })
    }
    
    /// Check system security status
    fn security_status(&self) -> PyResult<PySecurityStatus> {
        Ok(PySecurityStatus {
            sandbox_active: self.sandbox.is_active(),
            audit_logging_enabled: true,
            validator_enabled: true,
            platform: std::env::consts::OS.to_string(),
        })
    }
    
    /// Get recent security events
    fn get_audit_log(&self, limit: usize) -> Vec<String> {
        self.audit_logger.get_recent(limit)
            .into_iter()
            .map(|e| serde_json::to_string(&e).unwrap_or_default())
            .collect()
    }
}

#[pyclass]
#[derive(Clone)]
pub struct PyExecutionResult {
    #[pyo3(get)]
    pub success: bool,
    #[pyo3(get)]
    pub stdout: String,
    #[pyo3(get)]
    pub stderr: String,
    #[pyo3(get)]
    pub execution_time_ms: u64,
    #[pyo3(get)]
    pub memory_usage_mb: f64,
}

#[pyclass]
#[derive(Clone)]
pub struct PySecurityStatus {
    #[pyo3(get)]
    pub sandbox_active: bool,
    #[pyo3(get)]
    pub audit_logging_enabled: bool,
    #[pyo3(get)]
    pub validator_enabled: bool,
    #[pyo3(get)]
    pub platform: String,
}

/// Compute SHA256 hash of input
fn sha256(input: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(input.as_bytes());
    hex::encode(hasher.finalize())
}

/// Python module initialization
#[pymodule]
fn foundry_security(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SecurityEngine>()?;
    m.add_class::<PyExecutionResult>()?;
    m.add_class::<PySecurityStatus>()?;
    Ok(())
}
