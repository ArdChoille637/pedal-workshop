// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

public struct DashboardSummary: Codable, Sendable {
    public let totalComponents: Int
    public let totalUniqueParts: Int
    public let totalProjects: Int
    public let activeBuilds: Int
    public let lowStockCount: Int
    public let readyToBuild: Int
    public let arna13: Int
    public let arna4Plus: Int

    enum CodingKeys: String, CodingKey {
        case totalComponents  = "total_components"
        case totalUniqueParts = "total_unique_parts"
        case totalProjects    = "total_projects"
        case activeBuilds     = "active_builds"
        case lowStockCount    = "low_stock_count"
        case readyToBuild     = "ready_to_build"
        case arna13           = "arna_1_3"
        case arna4Plus        = "arna_4_plus"
    }
}

public struct CheapestSource: Codable, Sendable {
    public let supplier: String
    public let price: Double?
    public let inStock: Bool?
    enum CodingKeys: String, CodingKey {
        case supplier, price
        case inStock = "in_stock"
    }
}

public struct MissingPart: Codable, Identifiable, Sendable {
    public var id: Int { bomItemId }
    public let bomItemId: Int
    public let reference: String?
    public let category: String
    public let value: String
    public let shortfall: Int
    public let cheapestSource: CheapestSource?
    enum CodingKeys: String, CodingKey {
        case reference, category, value, shortfall
        case bomItemId      = "bom_item_id"
        case cheapestSource = "cheapest_source"
    }
}

public struct ProjectBuildStatus: Codable, Identifiable, Sendable {
    public var id: Int { projectId }
    public let projectId: Int
    public let projectName: String
    public let effectType: String?
    public let status: String
    public let bomCount: Int
    public let missingCount: Int
    public let missingParts: [MissingPart]
    public let estimatedCost: Double?
    enum CodingKeys: String, CodingKey {
        case status
        case projectId    = "project_id"
        case projectName  = "project_name"
        case effectType   = "effect_type"
        case bomCount     = "bom_count"
        case missingCount = "missing_count"
        case missingParts = "missing_parts"
        case estimatedCost = "estimated_cost"
    }
}

public struct BuildTiers: Codable, Sendable {
    public let ready: [ProjectBuildStatus]
    public let arna13: [ProjectBuildStatus]
    public let arna4Plus: [ProjectBuildStatus]
    enum CodingKeys: String, CodingKey {
        case ready
        case arna13   = "arna_1_3"
        case arna4Plus = "arna_4_plus"
    }
}
