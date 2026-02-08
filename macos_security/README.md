# Foundry Security for macOS

Native macOS security tools for The Foundry, implemented in Swift for optimal integration with macOS security features.

## Features

- **Native Sandbox**: Swift-based process isolation using macOS security features
- **Seatbelt Integration**: Optional sandbox-exec profile generation
- **Code Validation**: Static analysis for security threats
- **Audit Logging**: Immutable event log with integrity verification
- **Resource Limits**: Memory, CPU, and time restrictions

## Requirements

- macOS 12.0 (Monterey) or later
- Swift 5.7 or later
- Xcode 14 or later (for building)

## Building

```bash
cd macos_security
swift build
```

## Installation

```bash
swift build -c release
cp .build/release/foundry-sandbox /usr/local/bin/
```

## Usage

### Execute Code in Sandbox

```bash
foundry-sandbox execute script.py --timeout 30 --memory 512
```

### Validate Code

```bash
foundry-sandbox validate script.py
```

### View Audit Log

```bash
foundry-sandbox audit --limit 50
```

### Check Status

```bash
foundry-sandbox status
```

## Integration with Python

The Swift security tools complement the Python security module:

```python
from foundry.security import SecurityManager

# Uses Rust engine on Linux/Windows
# Uses Swift tools on macOS (if available)
security = SecurityManager()
result = security.validate_and_execute(code)
```

## Seatbelt Sandbox Profile

The Swift tools can generate seatbelt profiles for additional isolation:

```swift
let sandbox = FoundrySandbox()
let profile = sandbox.applySeatbeltSandbox()
// Profile can be used with sandbox-exec
```

## Security Features

### Sandboxing
- Process isolation
- Resource limits (memory, CPU, time)
- Filesystem restrictions
- Network access control

### Code Validation
- Forbidden import detection
- Path traversal detection
- Obfuscation detection
- Suspicious pattern matching

### Audit Logging
- Cryptographic integrity chains
- Tamper detection
- JSON export
- Statistics

## Differences from Python/Rust Implementation

| Feature | Python | Rust | Swift (macOS) |
|---------|--------|------|---------------|
| Process Isolation | subprocess | subprocess | Process API |
| Resource Limits | ulimit | ulimit | Process API |
| Filesystem | chroot (limited) | chroot (limited) | Seatbelt |
| Native UI | No | No | Yes (potential) |
| Performance | Good | Excellent | Excellent |
| Memory Safety | No | Yes | Yes |

## License

Proprietary - See main project LICENSE
