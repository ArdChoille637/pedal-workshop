// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

// MARK: – Form binding structs (not Codable, not persisted)

public struct ComponentForm: Sendable {
    public var category: String = "resistor"
    public var subcategory: String = ""
    public var value: String = ""
    public var valueUnit: String = ""
    public var package: String = ""
    public var description: String = ""
    public var manufacturer: String = ""
    public var mpn: String = ""
    public var quantity: Int = 0
    public var minQuantity: Int = 5
    public var location: String = ""
    public var notes: String = ""

    public init() {}

    public init(from component: Component) {
        self.category     = component.category
        self.subcategory  = component.subcategory ?? ""
        self.value        = component.value
        self.valueUnit    = component.valueUnit ?? ""
        self.package      = component.package ?? ""
        self.description  = component.description ?? ""
        self.manufacturer = component.manufacturer ?? ""
        self.mpn          = component.mpn ?? ""
        self.quantity     = component.quantity
        self.minQuantity  = component.minQuantity
        self.location     = component.location ?? ""
        self.notes        = component.notes ?? ""
    }
}

public struct ProjectForm: Sendable {
    public var name: String = ""
    public var effectType: String = ""
    public var status: String = "design"
    public var description: String = ""
    public var notes: String = ""

    public init() {}

    public init(name: String, effectType: String = "", status: String = "design",
                description: String = "", notes: String = "") {
        self.name = name; self.effectType = effectType; self.status = status
        self.description = description; self.notes = notes
    }

    public init(from project: Project) {
        self.name        = project.name
        self.effectType  = project.effectType ?? ""
        self.status      = project.status
        self.description = project.description ?? ""
        self.notes       = project.notes ?? ""
    }
}

public struct BOMItemForm: Sendable {
    public var reference: String = ""
    public var category: String = "resistor"
    public var value: String = ""
    public var quantity: Int = 1
    public var notes: String = ""
    public var isOptional: Bool = false
    public var componentId: Int? = nil

    public init() {}
}

// MARK: – Utility

extension String {
    public var nilIfEmpty: String? { isEmpty ? nil : self }
}
