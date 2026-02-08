# The Foundry Security Architecture
## Defense in Depth for AI Training Systems

---

## Executive Summary

The Foundry handles untrusted code execution during:
- Reward function evaluation (GRPO training)
- Code generation trajectory synthesis
- Sandbox tool execution

**Security is not optional — it's the foundation.**

---

## Threat Model

### Attack Vectors

| Vector | Risk | Mitigation |
|--------|------|------------|
| **Sandbox Escape** | Critical | Rust-based process isolation, namespace separation |
| **Resource Exhaustion** | High | Memory limits, CPU quotas, timeouts |
| **Data Exfiltration** | High | Network isolation, filesystem sandboxing |
| **Code Injection** | High | Static analysis, AST validation |
| **Persistence** | Medium | Ephemeral containers, no write access outside sandbox |
| **Side-Channel** | Low | Resource monitoring, behavioral analysis |

### Attack Scenarios

1. **Malicious Training Data**
   - Attacker submits code with `os.system("rm -rf /")`
   - → Caught by static validator before execution

2. **Sandbox Escape**
   - Attacker exploits Python import system
   - → Blocked by Rust security engine with syscall filtering

3. **Resource Exhaustion**
   - Attacker spawns infinite processes
   - → Limited by cgroup pids.max and monitored by behavioral analyzer

4. **Path Traversal**
   - Attacker tries `open("../../../etc/passwd")`
   → Blocked by chroot and path validation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LAYER 1: STATIC ANALYSIS (Python)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ CodeSecurityValidator                                                │   │
│  │  • AST parsing for forbidden imports                                 │   │
│  │  • Regex pattern matching for suspicious code                        │   │
│  │  • Obfuscation detection                                             │   │
│  │  • Path traversal detection                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  LAYER 2: RUST SECURITY ENGINE                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ foundry_security (Rust extension)                                    │   │
│  │  • Memory-safe sandbox implementation                                │   │
│  │  • Platform-specific isolation (cgroups/namespaces/job objects)      │   │
│  │  • Resource limits enforcement                                       │   │
│  │  • Behavioral threat detection                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  LAYER 3: PROCESS ISOLATION                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Sandbox Executor                                                     │   │
│  │  • Separate process with minimal privileges                          │   │
│  │  • Cleared environment variables                                     │   │
│  │  • Restricted filesystem access                                      │   │
│  │  • Network namespace isolation                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                              │
│  LAYER 4: AUDIT & MONITORING                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SecurityAuditLogger                                                  │   │
│  │  • Immutable append-only log (SQLite with integrity chains)          │   │
│  │  • Real-time threat detection                                        │   │
│  │  • Behavioral analysis                                               │   │
│  │  • Compliance reporting                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. CodeSecurityValidator (Python)

**Purpose:** Fast static analysis to catch obvious threats before execution.

**Capabilities:**
```python
validator = CodeSecurityValidator()
result = validator.validate(code)

if not result.is_safe:
    print(f"Blocked: {result.threats}")
```

**Detection Capabilities:**
- Forbidden imports (`os.system`, `subprocess`, `eval`, etc.)
- Path traversal patterns (`../`, absolute paths)
- Code obfuscation (base64, chr/ord encoding)
- Binary content detection
- Suspicious AST patterns

**Performance:** <10ms for typical code blocks

---

### 2. Rust Security Engine (`foundry_security`)

**Purpose:** Memory-safe, high-performance security engine.

**Why Rust:**
- Memory safety prevents entire classes of vulnerabilities
- Zero-cost abstractions for performance
- Direct OS API access for sandboxing
- Safe concurrency for monitoring

**Features:**
```rust
// Process isolation with resource limits
let sandbox = Sandbox::new(SandboxConfig {
    max_memory_mb: 512,
    max_cpu_time_sec: 30,
    max_processes: 10,
    allow_network: false,
})?;

// Execute with hard limits
let result = sandbox.execute(code, timeout_ms)?;
```

**Platform-Specific Implementation:**

**Linux:**
- `cgroups` for resource limiting (memory, CPU, pids)
- `namespaces` for isolation (pid, net, mount, user)
- `seccomp-bpf` for syscall filtering
- `chroot` or `pivot_root` for filesystem isolation

**Windows:**
- Job Objects for resource limits
- Windows Sandbox API
- ACL-based filesystem restrictions
- Windows Firewall for network isolation

---

### 3. SecurityAuditLogger

**Purpose:** Immutable, tamper-evident audit trail.

**Features:**
```python
logger = SecurityAuditLogger()

# Log events
logger.log(AuditEvent(
    event_type="CODE_EXECUTION",
    code_hash="abc123...",
    details={"threats_found": 0}
))

# Verify integrity
assert logger.verify_integrity()  # True if chain intact

# Export for compliance
logger.export_to_json(Path("audit_export.json"))
```

**Security Properties:**
- Append-only SQLite database
- Chain of cryptographic hashes linking events
- Tamper detection via integrity verification
- WAL mode for concurrent access

**Audit Events:**
- `CODE_EXECUTION_ATTEMPT` — Before validation
- `CODE_VALIDATION_FAILED` — Blocked by validator
- `CODE_EXECUTION_SUCCESS` — Successful sandbox execution
- `CODE_EXECUTION_FAILED` — Runtime failure
- `THREAT_DETECTED` — Behavioral analysis alert
- `POLICY_VIOLATION` — Resource limit exceeded
- `SANDBOX_ESCAPE_ATTEMPT` — Critical security event

---

### 4. Behavioral Analyzer

**Purpose:** Runtime threat detection via behavior monitoring.

**Threat Indicators:**
| ID | Name | Level | Pattern |
|----|------|-------|---------|
| THREAT-001 | Rapid File Access | Medium | >100 file ops/sec |
| THREAT-002 | Network Activity | High | Socket creation |
| THREAT-003 | Process Spawning | Medium | Child processes |
| THREAT-004 | Memory Exhaustion | High | >1GB allocation |
| THREAT-005 | Path Traversal | Critical | `../etc/passwd` |
| THREAT-006 | Env Var Access | Low | Reading secrets |

**Usage:**
```rust
let analyzer = BehavioralAnalyzer::new();
let result = analyzer.analyze(&execution_metrics);

if result.detected {
    println!("Threat: {}", result.recommendation);
}
```

---

## Integration with Training Pipeline

### GRPO Reward Function Execution

```python
from foundry.security import SecurityManager

security = SecurityManager()

# Code generated by model during GRPO training
generated_code = model.generate(prompt)

# Secure execution with full audit trail
result = security.validate_and_execute(
    code=generated_code,
    timeout_ms=5000,
    context={
        "training_run_id": run_id,
        "step": step_num,
    }
)

if result.success:
    reward = evaluate_output(result.stdout)
else:
    reward = 0.0  # Failed execution = no reward
```

### Trajectory Synthesis

```python
from foundry.security import SecureSandbox

sandbox = SecureSandbox()

# Execute tool calls from trajectory synthesis
tool_result = await sandbox.execute(
    code=tool_call.code,
    timeout=10
)

# Safe to feed back to teacher model
```

---

## Building the Rust Security Engine

### Prerequisites
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install maturin for Python bindings
pip install maturin
```

### Build
```bash
cd security_engine

# Development build
maturin develop

# Production build
maturin build --release

# Install wheel
pip install target/wheels/foundry_security*.whl
```

### Verify Installation
```python
from foundry_security import SecurityEngine

engine = SecurityEngine()
status = engine.security_status()
print(f"Sandbox active: {status.sandbox_active}")
```

---

## CLI Commands

```bash
# Check security status
foundry security status

# Validate code without execution
foundry security validate --file script.py

# View audit log
foundry security audit --recent 50

# Verify audit integrity
foundry security verify

# Run code in maximum security sandbox
foundry security execute --file script.py --timeout 30
```

---

## Security Checklist

### For Production Deployment

- [ ] Rust security engine built and installed
- [ ] Audit logging enabled and writing to persistent storage
- [ ] Resource limits configured (512MB RAM, 30s timeout default)
- [ ] Network access disabled in sandbox
- [ ] Filesystem restricted to temp directories
- [ ] Audit log integrity verified
- [ ] Behavioral monitoring active
- [ ] Incident response plan documented

### For Development

- [ ] Python validator working (no Rust required)
- [ ] Basic sandbox functional
- [ ] Audit logging to SQLite
- [ ] Code review of custom reward functions

---

## Future Enhancements

### Phase 2: Advanced Isolation
- [ ] Container-based sandboxing (Docker/Podman)
- [ ] Hardware-assisted virtualization (KVM)
- [ ] eBPF-based syscall monitoring
- [ ] GPU isolation for CUDA code

### Phase 3: ML-Powered Security
- [ ] Neural code analysis for novel threats
- [ ] Anomaly detection in execution patterns
- [ ] Automated threat signature generation

### Phase 4: Compliance & Certification
- [ ] SOC 2 Type II audit
- [ ] ISO 27001 certification
- [ ] FedRAMP authorization

---

## Summary

The Foundry's security architecture provides **defense in depth** through:

1. **Static Analysis** — Catch threats before execution
2. **Rust Engine** — Memory-safe, high-performance sandboxing
3. **Process Isolation** — OS-level containment
4. **Audit Logging** — Immutable, tamper-evident records
5. **Behavioral Analysis** — Runtime threat detection

**Security is not a feature. It's the foundation.**

---

## References

- [Rust Security Guidelines](https://doc.rust-lang.org/nomicon/)
- [Linux Namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [seccomp-bpf](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [Windows Job Objects](https://docs.microsoft.com/en-us/windows/win32/procthread/job-objects)
