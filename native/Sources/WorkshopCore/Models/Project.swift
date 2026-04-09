import Foundation

public struct Project: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public var name: String
    public var slug: String
    public var effectType: String?
    public var status: String
    public var description: String?
    public var notes: String?
    public var schematicId: Int?
    public var createdAt: String
    public var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, name, slug, status, description, notes
        case effectType  = "effect_type"
        case schematicId = "schematic_id"
        case createdAt   = "created_at"
        case updatedAt   = "updated_at"
    }
}

public struct BOMItem: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public let projectId: Int
    public var componentId: Int?
    public var reference: String?
    public var category: String
    public var value: String
    public var quantity: Int
    public var notes: String?
    public var isOptional: Int
    public let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, reference, category, value, quantity, notes
        case projectId   = "project_id"
        case componentId = "component_id"
        case isOptional  = "is_optional"
        case createdAt   = "created_at"
    }
}
