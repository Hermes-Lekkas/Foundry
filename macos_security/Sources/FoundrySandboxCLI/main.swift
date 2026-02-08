import Foundation
import FoundrySecurity

@main
struct FoundrySandboxCLI {
    static func main() async {
        let arguments = CommandLine.arguments
        
        guard arguments.count > 1 else {
            printUsage()
            exit(1)
        }
        
        let command = arguments[1]
        
        switch command {
        case "execute", "exec":
            await executeCommand(arguments: Array(arguments.dropFirst(2)))
            
        case "validate", "val":
            await validateCommand(arguments: Array(arguments.dropFirst(2)))
            
        case "audit":
            await auditCommand(arguments: Array(arguments.dropFirst(2)))
            
        case "status":
            await statusCommand()
            
        case "help", "-h", "--help":
            printUsage()
            
        default:
            print("Unknown command: \(command)")
            printUsage()
            exit(1)
        }
    }
    
    static func printUsage() {
        print("""
        Foundry Security Sandbox for macOS
        
        Usage: foundry-sandbox <command> [options]
        
        Commands:
          execute <file>    Execute Python file in sandbox
          validate <file>   Validate code without execution
          audit             Show recent audit events
          status            Show security status
          help              Show this help message
        
        Options:
          --timeout <sec>   Execution timeout (default: 30)
          --memory <mb>     Memory limit in MB (default: 512)
          --network         Allow network access
        
        Examples:
          foundry-sandbox execute script.py
          foundry-sandbox validate script.py --timeout 60
          foundry-sandbox audit --limit 50
        """)
    }
    
    static func executeCommand(arguments: [String]) async {
        guard let filePath = arguments.first else {
            print("Error: No file specified")
            exit(1)
        }
        
        let url = URL(fileURLWithPath: filePath)
        guard FileManager.default.fileExists(atPath: url.path),
              let code = try? String(contentsOf: url) else {
            print("Error: Cannot read file: \(filePath)")
            exit(1)
        }
        
        // Parse options
        var timeout: TimeInterval = 30
        var memoryMB: UInt64 = 512
        var allowNetwork = false
        
        var i = 1
        while i < arguments.count {
            switch arguments[i] {
            case "--timeout" where i + 1 < arguments.count:
                timeout = TimeInterval(arguments[i + 1]) ?? 30
                i += 2
            case "--memory" where i + 1 < arguments.count:
                memoryMB = UInt64(arguments[i + 1]) ?? 512
                i += 2
            case "--network":
                allowNetwork = true
                i += 1
            default:
                i += 1
            }
        }
        
        // Create sandbox
        let config = FoundrySandbox.Configuration(
            maxMemoryMB: memoryMB,
            maxWallTimeSeconds: UInt64(timeout),
            allowNetwork: allowNetwork
        )
        
        let sandbox = FoundrySandbox(configuration: config)
        
        print("Executing in sandbox...")
        print("  Memory: \(memoryMB) MB")
        print("  Timeout: \(timeout) seconds")
        print("  Network: \(allowNetwork ? "allowed" : "denied")")
        print("")
        
        let result = await sandbox.execute(code: code, timeout: timeout)
        
        print("Exit code: \(result.exitCode)")
        print("Execution time: \(result.executionTimeMs) ms")
        print("Timed out: \(result.timedOut)")
        print("")
        
        if !result.stdout.isEmpty {
            print("=== STDOUT ===")
            print(result.stdout)
        }
        
        if !result.stderr.isEmpty {
            print("=== STDERR ===")
            print(result.stderr)
        }
        
        exit(result.success ? 0 : 1)
    }
    
    static func validateCommand(arguments: [String]) async {
        guard let filePath = arguments.first else {
            print("Error: No file specified")
            exit(1)
        }
        
        let url = URL(fileURLWithPath: filePath)
        guard FileManager.default.fileExists(atPath: url.path),
              let code = try? String(contentsOf: url) else {
            print("Error: Cannot read file: \(filePath)")
            exit(1)
        }
        
        let validator = CodeValidator()
        let result = validator.validate(code: code)
        
        print("Validation Result:")
        print("  Safe: \(result.isSafe ? "YES" : "NO")")
        
        if !result.threats.isEmpty {
            print("  Threats:")
            for threat in result.threats {
                print("    - \(threat)")
            }
        }
        
        if !result.warnings.isEmpty {
            print("  Warnings:")
            for warning in result.warnings {
                print("    - \(warning)")
            }
        }
        
        exit(result.isSafe ? 0 : 1)
    }
    
    static func auditCommand(arguments: [String]) async {
        let logger = AuditLogger()
        
        var limit = 50
        if let limitIndex = arguments.firstIndex(where: { $0 == "--limit" }),
           limitIndex + 1 < arguments.count {
            limit = Int(arguments[limitIndex + 1]) ?? 50
        }
        
        let events = await logger.getRecent(limit: limit)
        
        print("Recent \(events.count) Audit Events:")
        print("")
        
        for event in events {
            let date = ISO8601DateFormatter().string(from: event.timestamp)
            print("[\(date)] \(event.eventType)")
            print("  Code Hash: \(event.codeHash.prefix(8))...")
            if !event.details.isEmpty {
                print("  Details: \(event.details)")
            }
            print("")
        }
        
        let stats = await logger.getStatistics()
        print("Statistics:")
        print("  Total events: \(stats["total_events"] ?? 0)")
        print("  Integrity: \(stats["integrity_verified"] as? Bool == true ? "✓ Verified" : "✗ Failed")")
    }
    
    static func statusCommand() async {
        print("Foundry Security Status (macOS)")
        print("")
        
        // Check sandbox availability
        let config = FoundrySandbox.Configuration()
        let sandbox = FoundrySandbox(configuration: config)
        
        print("Sandbox Configuration:")
        print("  Memory limit: \(config.maxMemoryMB) MB")
        print("  CPU time limit: \(config.maxCPUTimeSeconds) seconds")
        print("  Work directory: \(config.workDirectory.path)")
        print("  Network access: \(config.allowNetwork ? "allowed" : "denied")")
        print("")
        
        // Check audit logger
        let logger = AuditLogger()
        let stats = await logger.getStatistics()
        
        print("Audit Log:")
        print("  Total events: \(stats["total_events"] ?? 0)")
        print("  Integrity: \(stats["integrity_verified"] as? Bool == true ? "✓ Verified" : "✗ Failed")")
        print("")
        
        // Check seatbelt availability
        let seatbeltAvailable = FileManager.default.fileExists(atPath: "/usr/bin/sandbox-exec")
        print("Seatbelt Sandbox: \(seatbeltAvailable ? "Available" : "Not Available")")
        
        // Python availability
        let pythonAvailable = FileManager.default.fileExists(atPath: "/usr/bin/python3")
        print("Python3: \(pythonAvailable ? "Available" : "Not Available")")
    }
}
