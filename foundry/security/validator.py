# The Foundry - Proprietary Module
# Copyright (c) 2026 Hermes Lekkas
#
# This file is PROPRIETARY and SOURCE-AVAILABLE.
# You may view and use this code, but may not modify or redistribute it.
# See LICENSE file for full terms.

"""Code Security Validator — Static analysis for threats."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Code validation result."""
    is_safe: bool
    threats: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


class CodeSecurityValidator:
    """
    Static code analysis for security threats.
    
    Detects:
    - Dangerous imports (os.system, subprocess, etc.)
    - Path traversal attempts
    - Code obfuscation
    - Network operations
    - File system manipulation
    """
    
    # Forbidden imports
    FORBIDDEN_IMPORTS = {
        'os.system', 'os.popen', 'os.spawn', 'os.exec',
        'subprocess.call', 'subprocess.run', 'subprocess.Popen',
        'subprocess.check_output', 'subprocess.check_call',
        'eval', 'exec', 'compile', '__import__',
        'importlib.import_module', 'importlib.__import__',
        'ctypes', 'ctypes.CDLL', 'ctypes.cdll',
        'socket', 'socket.socket',
        'urllib.request.urlopen', 'urllib.urlopen',
        'http.client', 'ftplib', 'smtplib', 'telnetlib',
        'webbrowser', 'multiprocessing',
    }
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        (r'open\s*\(\s*["\']*/', 'Absolute path access'),
        (r'open\s*\(\s*["\']*\.\./', 'Parent directory traversal'),
        (r'__builtins__', 'Builtins manipulation'),
        (r'globals\(\)', 'Globals access'),
        (r'locals\(\)', 'Locals access'),
        (r'vars\(\)', 'Vars access'),
        (r'getattr\s*\([^,]+\s*,\s*["\']__', 'Private attribute access'),
        (r'setattr\s*\([^,]+\s*,\s*["\']__', 'Private attribute modification'),
        (r'base64\.(b64decode|decode)', 'Base64 decoding (possible obfuscation)'),
        (r'\bchr\s*\(\s*\d+\s*\)', 'Character code construction'),
        (r'\bexec\s*\(', 'Dynamic code execution'),
        (r'\beval\s*\(', 'Dynamic evaluation'),
    ]
    
    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern), desc) 
            for pattern, desc in self.SUSPICIOUS_PATTERNS
        ]
    
    def validate(self, code: str) -> ValidationResult:
        """Validate Python code for security threats."""
        threats = []
        warnings = []
        imports = []
        
        # Check syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_safe=False,
                threats=[f"Syntax error: {e}"],
            )
        
        # Extract imports
        imports = self._extract_imports(tree)
        
        # Check for forbidden imports
        for imp in imports:
            if imp in self.FORBIDDEN_IMPORTS:
                threats.append(f"Forbidden import: {imp}")
        
        # Check for suspicious patterns
        for pattern, description in self.compiled_patterns:
            if pattern.search(code):
                threats.append(f"{description}: {pattern.pattern[:30]}...")
        
        # Check for code obfuscation
        obfuscation_score = self._check_obfuscation(code)
        if obfuscation_score > 0.5:
            threats.append(f"Potential code obfuscation (score: {obfuscation_score:.2f})")
        elif obfuscation_score > 0.2:
            warnings.append(f"Possible obfuscation (score: {obfuscation_score:.2f})")
        
        # Check file operations
        file_ops = self._check_file_operations(tree)
        if file_ops:
            warnings.extend(file_ops)
        
        # Check for excessive length
        if len(code) > 100_000:
            warnings.append("Code exceeds 100KB")
        
        # Check for binary/encoded content
        if self._has_binary_content(code):
            threats.append("Binary or encoded content detected")
        
        return ValidationResult(
            is_safe=len(threats) == 0,
            threats=threats,
            warnings=warnings,
            imports=imports,
        )
    
    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Extract all imports from AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports.append(full_name)
            elif isinstance(node, ast.Call):
                # Check for __import__ calls
                if isinstance(node.func, ast.Name) and node.func.id == '__import__':
                    if node.args and isinstance(node.args[0], ast.Constant):
                        imports.append(f"__import__:{node.args[0].value}")
        
        return imports
    
    def _check_obfuscation(self, code: str) -> float:
        """Check for code obfuscation indicators."""
        score = 0.0
        
        # Count chr/ord usage
        chr_count = code.count('chr(')
        ord_count = code.count('ord(')
        if len(code) > 0:
            chr_ord_ratio = (chr_count + ord_count) / len(code) * 100
            if chr_ord_ratio > 0.5:
                score += min(0.5, chr_ord_ratio / 2)
        
        # Check for long encoded strings
        long_strings = re.findall(r'["\'][A-Za-z0-9+/]{100,}["\']', code)
        if long_strings:
            score += 0.3 * len(long_strings)
        
        # Check for variable name patterns (obfuscated names)
        obfuscated_vars = re.findall(r'\b[Oo0][0oO_]{2,}\b|\b[_]{3,}\w+\b', code)
        if obfuscated_vars:
            score += 0.2 * len(obfuscated_vars)
        
        return min(1.0, score)
    
    def _check_file_operations(self, tree: ast.AST) -> list[str]:
        """Check for potentially dangerous file operations."""
        warnings = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'open':
                        # Check for absolute paths
                        if node.args and isinstance(node.args[0], ast.Constant):
                            path = str(node.args[0].value)
                            if path.startswith('/') or path.startswith('\\'):
                                warnings.append(f"Absolute path in open(): {path[:30]}")
                            if '..' in path:
                                warnings.append(f"Parent directory traversal: {path[:30]}")
                    
                    elif node.func.id in ('rmtree', 'remove', 'unlink'):
                        warnings.append(f"File deletion: {node.func.id}")
        
        return warnings
    
    def _has_binary_content(self, code: str) -> bool:
        """Check for binary or encoded content."""
        # Check for null bytes
        if '\x00' in code:
            return True
        
        # Check for high ratio of non-printable characters
        non_printable = sum(1 for c in code if ord(c) < 32 and c not in '\n\r\t')
        if len(code) > 0 and non_printable / len(code) > 0.1:
            return True
        
        return False
