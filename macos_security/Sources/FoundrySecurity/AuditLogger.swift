import Foundation

/// Security audit event
public struct AuditEvent: Codable {
    public let id: UUID
    public let timestamp: Date
    public let eventType: String
    public let codeHash: String
    public let details: [String: String]
    public let integrityHash: String
    
    public init(
        eventType: String,
        codeHash: String,
        details: [String: String] = [:],
        previousHash: String = "0"
    ) {
        self.id = UUID()
        self.timestamp = Date()
        self.eventType = eventType
        self.codeHash = codeHash
        self.details = details
        
        // Compute integrity hash (chain of events)
        let data = "\(previousHash):\(timestamp):\(eventType):\(codeHash)"
        self.integrityHash = data.sha256()
    }
}

/// Security audit logger with integrity verification
public actor AuditLogger {
    private let logURL: URL
    private var events: [AuditEvent] = []
    private var lastHash: String = "0"
    
    public init(logPath: URL? = nil) {
        if let path = logPath {
            self.logURL = path
        } else {
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
            self.logURL = docs.appendingPathComponent("foundry_security_audit.json")
        }
        
        // Load existing events
        loadEvents()
    }
    
    /// Log a security event
    public func log(eventType: String, codeHash: String, details: [String: String] = [:]) {
        let event = AuditEvent(
            eventType: eventType,
            codeHash: codeHash,
            details: details,
            previousHash: lastHash
        )
        
        events.append(event)
        lastHash = event.integrityHash
        
        // Persist to disk
        saveEvents()
    }
    
    /// Get recent events
    public func getRecent(limit: Int = 100) -> [AuditEvent] {
        return Array(events.suffix(limit))
    }
    
    /// Verify integrity of the audit chain
    public func verifyIntegrity() -> Bool {
        var computedHash = "0"
        
        for event in events {
            let data = "\(computedHash):\(event.timestamp):\(event.eventType):\(event.codeHash)"
            let expectedHash = data.sha256()
            
            if event.integrityHash != expectedHash {
                return false
            }
            
            computedHash = expectedHash
        }
        
        return true
    }
    
    /// Export events to JSON
    public func export(to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted
        encoder.dateEncodingStrategy = .iso8601
        
        let data = try encoder.encode(events)
        try data.write(to: url)
    }
    
    /// Get statistics
    public func getStatistics() -> [String: Any] {
        let grouped = Dictionary(grouping: events) { $0.eventType }
        
        return [
            "total_events": events.count,
            "events_by_type": grouped.mapValues { $0.count },
            "integrity_verified": verifyIntegrity(),
            "first_event": events.first?.timestamp.timeIntervalSince1970 ?? 0,
            "last_event": events.last?.timestamp.timeIntervalSince1970 ?? 0
        ]
    }
    
    private func loadEvents() {
        guard FileManager.default.fileExists(atPath: logURL.path),
              let data = try? Data(contentsOf: logURL),
              let loaded = try? JSONDecoder().decode([AuditEvent].self, from: data) else {
            return
        }
        
        events = loaded
        lastHash = events.last?.integrityHash ?? "0"
    }
    
    private func saveEvents() {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        
        if let data = try? encoder.encode(events) {
            try? data.write(to: logURL)
        }
    }
}

// MARK: - String Extensions

private extension String {
    func sha256() -> String {
        let data = Data(self.utf8)
        var hash = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_SHA256($0.baseAddress, CC_LONG(data.count), &hash)
        }
        return hash.map { String(format: "%02x", $0) }.joined()
    }
}

// Import for SHA256
import CommonCrypto
