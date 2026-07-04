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
                // The schematic image/PDF library is packaged into the app bundle
                // so it's read from within the app — never from ~/Documents (which
                // would trigger the macOS Documents-folder permission prompt).
                // Populated locally by pipeline/tools/package_schematics.py;
                // gitignored (copyrighted + large). Ships empty on a fresh clone.
                .copy("Resources/Schematics"),
            ],
            swiftSettings: [
                .swiftLanguageMode(.v6)
            ]
        ),
    ]
)
