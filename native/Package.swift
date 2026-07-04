// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "WorkshopCore",
    platforms: [
        .macOS("26.0"),
    ],
    products: [
        .library(name: "WorkshopCore", targets: ["WorkshopCore"]),
    ],
    targets: [
        .target(
            name: "WorkshopCore",
            path: "Sources/WorkshopCore",
            resources: [
                .process("Resources/components.json"),
                .process("Resources/suppliers.json"),
                .process("Resources/projects.json"),
                .process("Resources/schematics.json"),
            ],
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
    ]
)
