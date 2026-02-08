import Foundation

/// macOS-native security sandbox for The Foundry
public actor FoundrySandbox {
    
    /// Sandbox configuration
    public struct Configuration {
        public var maxMemoryMB: UInt64
        public var maxCPUTimeSeconds: UInt64
        public var maxWallTimeSeconds: UInt64
        public var maxFileSizeMB: UInt64
        public var allowNetwork: Bool
        public var workDirectory: URL
        
        public init(
            maxMemoryMB: UInt64 = 512,
            maxCPUTimeSeconds: UInt64 = 30,
            maxWallTimeSeconds: UInt64 = 30,
            maxFileSizeMB: UInt64 = 100,
            allowNetwork: Bool = false,
            workDirectory: URL? = nil
        ) {
            self.maxMemoryMB = maxMemoryMB
            self.maxCPUTimeSeconds = maxCPUTimeSeconds
            self.maxWallTimeSeconds = maxWallTimeSeconds
            self.maxFileSizeMB = maxFileSizeMB
            self.allowNetwork = allowNetwork
            self.workDirectory = workDirectory ?? FileManager.default.temporaryDirectory
                .appendingPathComponent("foundry_sandbox_\(UUID().uuidString)")
        }
    }
    
    /// Execution result
    public struct ExecutionResult {
        public let success: Bool
        public let stdout: String
        public let stderr: String
        public let exitCode: Int32
        public let executionTimeMs: UInt64
        public let timedOut: Bool
    }
    
    private let config: Configuration
    private var activeProcesses: [Process] = []
    
    public init(configuration: Configuration = Configuration()) {
        self.config = configuration
        try? FileManager.default.createDirectory(
            at: config.workDirectory,
            withIntermediateDirectories: true
        )
    }
    
    /// Execute Python code in sandbox
    public func execute(code: String, timeout: TimeInterval? = nil) async -> ExecutionResult {
        let scriptPath = config.workDirectory.appendingPathComponent("script.py")
        
        // Write script
        do {
            try code.write(to: scriptPath, atomically: true, encoding: .utf8)
        } catch {
            return ExecutionResult(
                success: false,
                stdout: "",
                stderr: "Failed to write script: \(error)",
                exitCode: -1,
                executionTimeMs: 0,
                timedOut: false
            )
        }
        
        let startTime = Date()
        let timeout = timeout ?? TimeInterval(config.maxWallTimeSeconds)
        
        // Create process
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = [scriptPath.path]
        process.currentDirectoryURL = config.workDirectory
        
        // Environment
        var env = ProcessInfo.processInfo.environment
        env["HOME"] = config.workDirectory.path
        env["TMPDIR"] = config.workDirectory.path
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = ""
        process.environment = env
        
        // Pipes for output
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe
        
        // Resource limits using posix_spawn attributes would go here
        // For now, we rely on timeout-based termination
        
        // Execute with timeout
        do {
            try process.run()
            activeProcesses.append(process)
            
            // Wait with timeout
            let semaphore = DispatchSemaphore(value: 0)
            var timedOut = false
            
            process.terminationHandler = { _ in
                semaphore.signal()
            }
            
            DispatchQueue.global().async {
                Thread.sleep(forTimeInterval: timeout)
                if process.isRunning {
                    timedOut = true
                    process.terminate()
                }
            }
            
            semaphore.wait()
            activeProcesses.removeAll { $0 === process }
            
            let executionTime = UInt64(Date().timeIntervalSince(startTime) * 1000)
            
            // Read output
            let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
            let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
            
            let stdout = String(data: stdoutData, encoding: .utf8) ?? ""
            let stderr = String(data: stderrData, encoding: .utf8) ?? ""
            
            // Cleanup
            try? FileManager.default.removeItem(at: scriptPath)
            
            return ExecutionResult(
                success: process.terminationStatus == 0 && !timedOut,
                stdout: stdout,
                stderr: stderr,
                exitCode: process.terminationStatus,
                executionTimeMs: executionTime,
                timedOut: timedOut
            )
            
        } catch {
            return ExecutionResult(
                success: false,
                stdout: "",
                stderr: "Execution failed: \(error)",
                exitCode: -1,
                executionTimeMs: 0,
                timedOut: false
            )
        }
    }
    
    /// Generate and apply seatbelt sandbox profile
    public func applySeatbeltSandbox() -> String {
        let profile = """
        (version 1)
        (debug deny)
        
        ; Allow basic operations
        (allow default)
        
        ; Deny all file writes outside work directory
        (deny file-write*
            (subpath "/")
            (subpath "/System")
            (subpath "/usr")
            (subpath "/bin")
            (subpath "/sbin")
            (subpath "/private"))
        
        ; Allow writes only in work directory
        (allow file-write*
            (subpath "\(config.workDirectory.path)"))
        
        ; Allow reads from standard locations
        (allow file-read*
            (subpath "/System")
            (subpath "/usr")
            (subpath "/Library")
            (subpath "/dev")
            (subpath "/private/var")
            (subpath "\(config.workDirectory.path)"))
        
        ; Network access
        \(config.allowNetwork ? "(allow network*)" : "(deny network*)")
        
        ; Deny process creation
        (deny process-exec
            (subpath "/bin")
            (subpath "/usr/bin")
            (subpath "/sbin")
            (subpath "/usr/sbin"))
        """
        
        return profile
    }
    
    /// Cleanup sandbox directory
    public func cleanup() {
        for process in activeProcesses where process.isRunning {
            process.terminate()
        }
        activeProcesses.removeAll()
        
        try? FileManager.default.removeItem(at: config.workDirectory)
    }
}

/// Security validator for code analysis
public struct CodeValidator {
    
    public struct ValidationResult {
        public let isSafe: Bool
        public let threats: [String]
        public let warnings: [String]
    }
    
    private let forbiddenImports: Set<String> = [
        "os.system", "subprocess.call", "subprocess.run", "subprocess.Popen",
        "eval", "exec", "compile", "__import__", "importlib",
        "ctypes", "socket", "urllib.request", "http.client"
    ]
    
    public init() {}
    
    public func validate(code: String) -> ValidationResult {
        var threats: [String] = []
        var warnings: [String] = []
        
        // Check for forbidden imports
        for forbidden in forbiddenImports {
            if code.contains(forbidden) {
                threats.append("Forbidden import/pattern: \(forbidden)")
            }
        }
        
        // Check for path traversal
        if code.contains("../") || code.contains("..") {
            threats.append("Potential path traversal detected")
        }
        
        // Check for obfuscation patterns
        let chrCount = code.components(separatedBy: "chr(").count - 1
        let ordCount = code.components(separatedBy: "ord(").count - 1
        if chrCount + ordCount > 5 {
            warnings.append("Possible code obfuscation (chr/ord usage)")
        }
        
        // Check for base64 patterns
        if code.contains("base64.b64decode") || code.contains("decode('base64')") {
            warnings.append("Base64 decoding detected")
        }
        
        return ValidationResult(
            isSafe: threats.isEmpty,
            threats: threats,
            warnings: warnings
        )
    }
}
