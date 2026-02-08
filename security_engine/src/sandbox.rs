//! Sandbox Module
//! 
//! Platform-specific process isolation and resource limiting.

use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SandboxError {
    #[error("Failed to create sandbox: {0}")]
    CreationError(String),
    #[error("Execution timeout")]
    Timeout,
    #[error("Memory limit exceeded")]
    MemoryExceeded,
    #[error("Process error: {0}")]
    ProcessError(String),
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

/// Sandbox configuration
#[derive(Debug, Clone)]
pub struct SandboxConfig {
    /// Maximum memory in MB
    pub max_memory_mb: u64,
    /// Maximum CPU time in seconds
    pub max_cpu_time_sec: u64,
    /// Maximum wall clock time in milliseconds
    pub max_wall_time_ms: u64,
    /// Working directory
    pub work_dir: PathBuf,
    /// Network access allowed
    pub allow_network: bool,
    /// Maximum number of processes
    pub max_processes: u32,
    /// Maximum file size in MB
    pub max_file_size_mb: u64,
    /// Maximum open files
    pub max_open_files: u32,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        Self {
            max_memory_mb: 512,
            max_cpu_time_sec: 30,
            max_wall_time_ms: 30000,
            work_dir: std::env::temp_dir().join("foundry_sandbox"),
            allow_network: false,
            max_processes: 10,
            max_file_size_mb: 100,
            max_open_files: 64,
        }
    }
}

/// Execution result
#[derive(Debug, Clone)]
pub struct ExecutionResult {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
    pub execution_time_ms: u64,
    pub memory_usage_mb: f64,
    pub timed_out: bool,
}

/// Platform-agnostic sandbox
pub struct Sandbox {
    config: SandboxConfig,
    active: bool,
}

impl Sandbox {
    /// Create a new sandbox with the given configuration
    pub fn new(config: SandboxConfig) -> Result<Self, SandboxError> {
        std::fs::create_dir_all(&config.work_dir)?;
        
        Ok(Self {
            config,
            active: true,
        })
    }
    
    /// Check if sandbox is active
    pub fn is_active(&self) -> bool {
        self.active
    }
    
    /// Execute code in the sandbox
    pub fn execute(&self, code: &str, timeout_ms: u64) -> Result<ExecutionResult, SandboxError> {
        let script_path = self.config.work_dir.join("script.py");
        std::fs::write(&script_path, code)?;
        
        let mut cmd = Command::new("python");
        cmd.arg(&script_path)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .current_dir(&self.config.work_dir);
        
        // Minimal environment for security
        cmd.env_clear();
        if let Ok(path) = std::env::var("PATH") {
            cmd.env("PATH", path);
        }
        cmd.env("HOME", &self.config.work_dir);
        cmd.env("PYTHONDONTWRITEBYTECODE", "1");
        
        // Apply resource limits via shell wrapper on Unix (Linux/macOS)
        #[cfg(unix)]
        let mut cmd = {
            let is_macos = std::env::consts::OS == "macos";
            
            // macOS uses different resource limit syntax for some options
            let memory_limit = if is_macos {
                // macOS uses bytes instead of KB for some ulimit versions
                format!("ulimit -v {} 2>/dev/null || true", self.config.max_memory_mb * 1024)
            } else {
                format!("ulimit -v {} 2>/dev/null", self.config.max_memory_mb * 1024)
            };
            
            let limit_script = format!(
                "{}; ulimit -t {} 2>/dev/null; ulimit -n {} 2>/dev/null; exec python3 '{}'",
                memory_limit,
                self.config.max_cpu_time_sec,
                self.config.max_open_files,
                script_path.display()
            );
            
            let mut c = Command::new("sh");
            c.arg("-c").arg(&limit_script)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .current_dir(&self.config.work_dir);
            c.env_clear();
            c.env("PATH", std::env::var("PATH").unwrap_or_default());
            c.env("HOME", &self.config.work_dir);
            c.env("TMPDIR", &self.config.work_dir);
            c.env("PYTHONDONTWRITEBYTECODE", "1");
            
            // macOS-specific environment
            if is_macos {
                if let Ok(cf_encoding) = std::env::var("__CF_USER_TEXT_ENCODING") {
                    c.env("__CF_USER_TEXT_ENCODING", cf_encoding);
                }
            }
            
            c
        };
        
        let mut child = cmd.spawn()?;
        let result = self.wait_with_timeout(&mut child, timeout_ms)?;
        
        let _ = std::fs::remove_file(&script_path);
        
        Ok(result)
    }
    
    /// Wait for child process with timeout
    fn wait_with_timeout(
        &self,
        child: &mut std::process::Child,
        timeout_ms: u64
    ) -> Result<ExecutionResult, SandboxError> {
        let start = Instant::now();
        let timeout = Duration::from_millis(timeout_ms);
        
        let status = loop {
            match child.try_wait()? {
                Some(status) => break status,
                None => {
                    if start.elapsed() > timeout {
                        child.kill()?;
                        child.wait()?;
                        return Ok(ExecutionResult {
                            success: false,
                            stdout: String::new(),
                            stderr: "Execution timed out".to_string(),
                            exit_code: -1,
                            execution_time_ms: timeout_ms,
                            memory_usage_mb: 0.0,
                            timed_out: true,
                        });
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
        };
        
        let elapsed = start.elapsed().as_millis() as u64;
        
        let stdout = child.stdout.take()
            .and_then(|mut s| {
                let mut buf = String::new();
                std::io::Read::read_to_string(&mut s, &mut buf).ok()?;
                Some(buf)
            })
            .unwrap_or_default();
        
        let stderr = child.stderr.take()
            .and_then(|mut s| {
                let mut buf = String::new();
                std::io::Read::read_to_string(&mut s, &mut buf).ok()?;
                Some(buf)
            })
            .unwrap_or_default();
        
        Ok(ExecutionResult {
            success: status.success(),
            stdout,
            stderr,
            exit_code: status.code().unwrap_or(-1),
            execution_time_ms: elapsed,
            memory_usage_mb: 0.0,
            timed_out: false,
        })
    }
}
