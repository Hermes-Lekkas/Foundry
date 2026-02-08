//! Validator Module
//! 
//! Static analysis for detecting malicious or unsafe code patterns.

use regex::Regex;
use std::collections::HashSet;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ValidationError {
    #[error("Syntax error: {0}")]
    SyntaxError(String),
    #[error("Validation failed: {0}")]
    ValidationFailed(String),
}

/// Validation result
#[derive(Debug, Clone)]
pub struct ValidationResult {
    pub is_safe: bool,
    pub threats: Vec<String>,
    pub warnings: Vec<String>,
    pub imports: Vec<String>,
    pub function_calls: Vec<String>,
}

/// Code validator
pub struct CodeValidator {
    forbidden_imports: HashSet<String>,
    forbidden_patterns: Vec<Regex>,
    suspicious_patterns: Vec<Regex>,
}

impl CodeValidator {
    /// Create a new validator with default security rules
    pub fn new() -> Self {
        let forbidden_imports: HashSet<String> = [
            "os.system", "subprocess.call", "subprocess.run",
            "subprocess.Popen", "eval", "exec", "compile",
            "__import__", "importlib", "ctypes", "socket",
            "urllib.request", "http.client", "ftplib", "smtplib",
            "shutil.rmtree", "shutil.copy", "shutil.move",
            "multiprocessing", "threading", "asyncio.subprocess",
        ].iter().map(|s| s.to_string()).collect();
        
        let forbidden_patterns = vec![
            Regex::new(r"open\s*\(\s*['\"]*/").unwrap(), // Absolute path access
            Regex::new(r"open\s*\(\s*['\"]\.\./").unwrap(), // Parent directory access
            Regex::new(r"__builtins__").unwrap(),
            Regex::new(r"globals\(\)").unwrap(),
            Regex::new(r"locals\(\)").unwrap(),
            Regex::new(r"vars\(\)").unwrap(),
        ];
        
        let suspicious_patterns = vec![
            Regex::new(r"base64\.(b64decode|decode)").unwrap(),
            Regex::new(r"\bbytes\._").unwrap(),
            Regex::new(r"\bobject\.__").unwrap(),
            Regex::new(r"class.*__del__").unwrap(),
        ];
        
        Self {
            forbidden_imports,
            forbidden_patterns,
            suspicious_patterns,
        }
    }
    
    /// Validate Python code
    pub fn validate_python(&self, code: &str) -> Result<ValidationResult, ValidationError> {
        let mut threats = Vec::new();
        let mut warnings = Vec::new();
        let mut imports = Vec::new();
        let mut function_calls = Vec::new();
        
        // Extract imports
        self.extract_imports(code, &mut imports);
        
        // Check for forbidden imports
        for imp in &imports {
            if self.forbidden_imports.contains(imp) {
                threats.push(format!("Forbidden import: {}", imp));
            }
        }
        
        // Check for forbidden patterns
        for pattern in &self.forbidden_patterns {
            if pattern.is_match(code) {
                threats.push(format!("Forbidden pattern detected: {}", pattern.as_str()));
            }
        }
        
        // Check for suspicious patterns
        for pattern in &self.suspicious_patterns {
            if pattern.is_match(code) {
                warnings.push(format!("Suspicious pattern: {}", pattern.as_str()));
            }
        }
        
        // Check for code obfuscation
        if self.is_obfuscated(code) {
            threats.push("Potential code obfuscation detected".to_string());
        }
        
        // Check for excessive length (might be hiding something)
        if code.len() > 100_000 {
            warnings.push("Code exceeds 100KB - unusual for training examples".to_string());
        }
        
        let is_safe = threats.is_empty();
        
        Ok(ValidationResult {
            is_safe,
            threats,
            warnings,
            imports,
            function_calls,
        })
    }
    
    /// Extract imports from Python code
    fn extract_imports(&self, code: &str, imports: &mut Vec<String>) {
        // Match 'import X' and 'from X import Y'
        let import_regex = Regex::new(r"(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)").unwrap();
        
        for cap in import_regex.captures_iter(code) {
            if let Some(matched) = cap.get(1) {
                imports.push(matched.as_str().to_string());
            }
        }
    }
    
    /// Check if code appears obfuscated
    fn is_obfuscated(&self, code: &str) -> bool {
        // Check for excessive use of chr/ord
        let chr_count = code.matches("chr(").count();
        let ord_count = code.matches("ord(").count();
        let total_len = code.len();
        
        if total_len > 0 {
            let obfuscation_ratio = (chr_count + ord_count) as f64 / total_len as f64;
            if obfuscation_ratio > 0.01 {
                return true;
            }
        }
        
        // Check for base64-like strings
        let base64_pattern = Regex::new(r"[A-Za-z0-9+/]{50,}={0,2}").unwrap();
        if base64_pattern.is_match(code) {
            return true;
        }
        
        false
    }
    
    /// Validate code syntax
    pub fn check_syntax(&self, code: &str) -> Result<(), ValidationError> {
        // This would ideally use Python's parser
        // For now, do basic checks
        
        // Check for balanced parentheses
        let open_parens = code.matches('(').count();
        let close_parens = code.matches(')').count();
        if open_parens != close_parens {
            return Err(ValidationError::SyntaxError(
                "Unbalanced parentheses".to_string()
            ));
        }
        
        // Check for balanced brackets
        let open_brackets = code.matches('[').count();
        let close_brackets = code.matches(']').count();
        if open_brackets != close_brackets {
            return Err(ValidationError::SyntaxError(
                "Unbalanced brackets".to_string()
            ));
        }
        
        // Check for balanced braces
        let open_braces = code.matches('{').count();
        let close_braces = code.matches('}').count();
        if open_braces != close_braces {
            return Err(ValidationError::SyntaxError(
                "Unbalanced braces".to_string()
            ));
        }
        
        Ok(())
    }
}

impl Default for CodeValidator {
    fn default() -> Self {
        Self::new()
    }
}
