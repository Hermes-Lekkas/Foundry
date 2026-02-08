// swift-tools-version:5.7
// The Swift Tools Version.

import PackageDescription

let package = Package(
    name: "FoundrySecurity",
    platforms: [
        .macOS(.v12)
    ],
    products: [
        .library(
            name: "FoundrySecurity",
            targets: ["FoundrySecurity"]
        ),
        .executable(
            name: "foundry-sandbox",
            targets: ["FoundrySandboxCLI"]
        ),
    ],
    dependencies: [],
    targets: [
        .target(
            name: "FoundrySecurity",
            dependencies: []
        ),
        .executableTarget(
            name: "FoundrySandboxCLI",
            dependencies: ["FoundrySecurity"]
        ),
        .testTarget(
            name: "FoundrySecurityTests",
            dependencies: ["FoundrySecurity"]
        ),
    ]
)
