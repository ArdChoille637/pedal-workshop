// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

public struct Component: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public var category: String
    public var subcategory: String?
    public var value: String
    public var valueNumeric: Double?
    public var valueUnit: String?
    public var package: String?
    public var description: String?
    public var manufacturer: String?
    public var mpn: String?
    public var quantity: Int
    public var minQuantity: Int
    public var location: String?
    public var notes: String?
    public var createdAt: String
    public var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, category, subcategory, value, package, description,
             manufacturer, mpn, quantity, notes, location
        case valueNumeric  = "value_numeric"
        case valueUnit     = "value_unit"
        case minQuantity   = "min_quantity"
        case createdAt     = "created_at"
        case updatedAt     = "updated_at"
    }

    public var isLowStock: Bool { minQuantity > 0 && quantity < minQuantity }
}

public struct QuantityAdjust: Codable, Sendable {
    public let delta: Int
    public let reason: String
    public let note: String?
    public init(delta: Int, reason: String = "adjustment", note: String? = nil) {
        self.delta = delta; self.reason = reason; self.note = note
    }
}
