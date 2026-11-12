// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

/// A customer you build or repair pedals for.
/// PRIVACY: stored only in ~/Library/Application Support/PedalWorkshop/clients.json.
/// There is deliberately no bundle seed — customer data must never enter the repo.
public struct Client: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public var name: String
    public var email: String?
    public var phone: String?
    public var notes: String?
    public let createdAt: String
    public var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, name, email, phone, notes
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

public enum JobKind: String, Codable, CaseIterable, Sendable {
    case build, repair, mod
}

public enum JobStatus: String, Codable, CaseIterable, Sendable {
    case quoted, accepted, inProgress = "in_progress", ready, delivered, cancelled

    public var label: String {
        switch self {
        case .inProgress: "In progress"
        default: rawValue.capitalized
        }
    }
    /// Jobs still needing work or hand-off.
    public var isOpen: Bool { self != .delivered && self != .cancelled }
}

/// A build / repair / mod done for a client. Optionally linked to a Project
/// (the pedal design) so the BOM and stock tracking carry over.
public struct Job: Codable, Identifiable, Hashable, Sendable {
    public let id: Int
    public var clientId: Int
    public var projectId: Int?
    public var kind: JobKind
    public var title: String
    public var status: JobStatus
    public var quote: Double?
    public var deposit: Double?
    public var dueDate: String?      // ISO date, yyyy-MM-dd
    public var notes: String?
    public let createdAt: String
    public var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, kind, title, status, quote, deposit, notes
        case clientId  = "client_id"
        case projectId = "project_id"
        case dueDate   = "due_date"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

public struct ClientForm: Sendable {
    public var name = ""
    public var email = ""
    public var phone = ""
    public var notes = ""
    public init() {}
    public init(from c: Client) {
        name = c.name; email = c.email ?? ""; phone = c.phone ?? ""; notes = c.notes ?? ""
    }
}

public struct JobForm: Sendable {
    public var projectId: Int? = nil
    public var kind: JobKind = .build
    public var title = ""
    public var status: JobStatus = .quoted
    public var quote: Double? = nil
    public var deposit: Double? = nil
    public var dueDate = ""
    public var notes = ""
    public init() {}
}
