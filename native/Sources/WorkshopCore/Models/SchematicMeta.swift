import Foundation

/// OCR-extracted metadata for a single schematic file.
/// Loaded from schematics_metadata.json in Application Support.
public struct SchematicMeta: Codable, Identifiable, Sendable {
    public let id: Int
    public let fileName: String
    public let categoryFolder: String
    public let fileType: String
    public let filePath: String
    public let textExcerpt: String
    public let refsFound: [String]
    public let bomEntries: [OCRBOMEntry]
    public let bomCount: Int
    public let analyzed: Bool

    enum CodingKeys: String, CodingKey {
        case id, analyzed
        case fileName      = "file_name"
        case categoryFolder = "category_folder"
        case fileType      = "file_type"
        case filePath      = "file_path"
        case textExcerpt   = "text_excerpt"
        case refsFound     = "refs_found"
        case bomEntries    = "bom_entries"
        case bomCount      = "bom_count"
    }
}

/// A single component entry extracted from OCR.
public struct OCRBOMEntry: Codable, Sendable {
    public let category: String
    public let value: String
    public let quantity: Int
    public let source: String
}
