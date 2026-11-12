// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

/// Clients on the left, their jobs (build / repair / mod) on the right.
struct ClientsView: View {
    @Environment(WorkshopStore.self) private var store
    @State private var selectedId: Int?
    @State private var showNewClient = false
    @State private var showNewJob = false
    @State private var clientToDelete: Client?

    private var selected: Client? { store.clients.first { $0.id == selectedId } }

    var body: some View {
        HSplitView {
            List(selection: $selectedId) {
                ForEach(store.clients) { c in
                    HStack {
                        Text(c.name)
                        Spacer()
                        if openCount(c) > 0 {
                            Text("\(openCount(c)) open").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .tag(c.id)
                    .contextMenu { deleteButton(for: c) }
                }
            }
            .frame(minWidth: 220, idealWidth: 260)
            .overlay { if store.clients.isEmpty { ContentUnavailableView("No clients yet", systemImage: "person.2") } }

            Group {
                if let c = selected { detail(for: c) }
                else { ContentUnavailableView("Select a client", systemImage: "person") }
            }
            .frame(minWidth: 380)
        }
        .navigationTitle("Clients")
        .toolbar {
            Button { showNewClient = true } label: { Label("New Client", systemImage: "plus") }
        }
        .sheet(isPresented: $showNewClient) { ClientSheet(existing: nil) }
        .sheet(isPresented: $showNewJob) { if let c = selected { JobSheet(client: c) } }
        .confirmationDialog("Delete \(clientToDelete?.name ?? "")?", isPresented: .constant(clientToDelete != nil),
                            presenting: clientToDelete) { c in
            Button("Delete client and their jobs", role: .destructive) {
                Task { await store.deleteClient(c); clientToDelete = nil; selectedId = nil }
            }
            Button("Cancel", role: .cancel) { clientToDelete = nil }
        } message: { _ in Text("This can't be undone.") }
    }

    private func deleteButton(for c: Client) -> some View {
        Button("Delete…", role: .destructive) { clientToDelete = c }
    }

    private func openCount(_ c: Client) -> Int {
        store.jobs.filter { $0.clientId == c.id && $0.status.isOpen }.count
    }

    private func subtitle(for j: Job) -> String {
        var parts: [String] = [j.kind.rawValue.capitalized]
        if let q = j.quote { parts.append(String(format: "$%.2f", q)) }
        if let d = j.dueDate { parts.append("due \(d)") }
        return parts.joined(separator: " · ")
    }

    @ViewBuilder
    private func detail(for c: Client) -> some View {
        let jobs = store.jobs.filter { $0.clientId == c.id }
        VStack(alignment: .leading, spacing: 12) {
            Text(c.name).font(.title2.bold())
            if let e = c.email { Label(e, systemImage: "envelope") }
            if let p = c.phone { Label(p, systemImage: "phone") }
            if let n = c.notes { Text(n).foregroundStyle(.secondary) }
            Divider()
            HStack {
                Text("Jobs").font(.headline)
                Spacer()
                Button { showNewJob = true } label: { Label("New Job", systemImage: "plus") }
            }
            List(jobs) { j in
                HStack {
                    VStack(alignment: .leading) {
                        Text(j.title)
                        Text(subtitle(for: j))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Picker("", selection: Binding(
                        get: { j.status },
                        set: { var u = j; u.status = $0; Task { await store.updateJob(u) } })) {
                        ForEach(JobStatus.allCases, id: \.self) { Text($0.label).tag($0) }
                    }.labelsHidden().frame(width: 130)
                    Button(role: .destructive) { Task { await store.deleteJob(j) } } label: { Image(systemName: "trash") }
                        .buttonStyle(.borderless)
                }
            }
        }
        .padding()
    }
}

private struct ClientSheet: View {
    @Environment(WorkshopStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let existing: Client?
    @State private var form = ClientForm()

    var body: some View {
        Form {
            TextField("Name", text: $form.name)
            TextField("Email", text: $form.email)
            TextField("Phone", text: $form.phone)
            TextField("Notes", text: $form.notes, axis: .vertical)
            HStack {
                Button("Cancel", role: .cancel) { dismiss() }
                Button("Save") {
                    Task { await store.addClient(form); dismiss() }
                }.disabled(form.name.trimmingCharacters(in: .whitespaces).isEmpty)
                 .keyboardShortcut(.defaultAction)
            }
        }
        .padding().frame(width: 380)
    }
}

private struct JobSheet: View {
    @Environment(WorkshopStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let client: Client
    @State private var form = JobForm()

    var body: some View {
        Form {
            TextField("Title (e.g. Fuzz Face build)", text: $form.title)
            Picker("Type", selection: $form.kind) {
                ForEach(JobKind.allCases, id: \.self) { Text($0.rawValue.capitalized).tag($0) }
            }
            Picker("Pedal project", selection: $form.projectId) {
                Text("None").tag(Int?.none)
                ForEach(store.projects) { Text($0.name).tag(Int?.some($0.id)) }
            }
            TextField("Quote ($)", value: $form.quote, format: .number)
            TextField("Deposit ($)", value: $form.deposit, format: .number)
            TextField("Due date (yyyy-MM-dd)", text: $form.dueDate)
            TextField("Notes", text: $form.notes, axis: .vertical)
            HStack {
                Button("Cancel", role: .cancel) { dismiss() }
                Button("Save") {
                    Task { await store.addJob(form, for: client); dismiss() }
                }.disabled(form.title.trimmingCharacters(in: .whitespaces).isEmpty)
                 .keyboardShortcut(.defaultAction)
            }
        }
        .padding().frame(width: 400)
    }
}
