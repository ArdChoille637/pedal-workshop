// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

public struct Supplier: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public var name: String
    public var slug: String
    public var website: String?
    public var apiType: String
    public var pollEnabled: Int
    public var pollInterval: Int
    public var lastPolledAt: String?
    public let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, name, slug, website
        case apiType      = "api_type"
        case pollEnabled  = "poll_enabled"
        case pollInterval = "poll_interval"
        case lastPolledAt = "last_polled_at"
        case createdAt    = "created_at"
    }
}

// MARK: – Supplier listing (saved price + SKU link)

public struct SupplierListing: Codable, Identifiable, Sendable {
    public let id: Int
    public var supplierId: Int
    public var componentId: Int?
    public var sku: String
    public var title: String
    public var price: Double
    public var currency: String
    public var inStock: Bool
    public var url: String?
    public var lastChecked: String

    enum CodingKeys: String, CodingKey {
        case id, sku, title, price, currency, url
        case supplierId  = "supplier_id"
        case componentId = "component_id"
        case inStock     = "in_stock"
        case lastChecked = "last_checked"
    }
}

// MARK: – Schematic

public struct Schematic: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public let categoryFolder: String
    public let fileName: String
    public let filePath: String
    public let fileType: String
    public let fileSize: Int?
    public let effectType: String?
    public let tags: String?
    public let createdAt: String?

    enum CodingKeys: String, CodingKey {
        case id, tags
        case categoryFolder = "category_folder"
        case fileName       = "file_name"
        case filePath       = "file_path"
        case fileType       = "file_type"
        case fileSize       = "file_size"
        case effectType     = "effect_type"
        case createdAt      = "created_at"
    }
}
