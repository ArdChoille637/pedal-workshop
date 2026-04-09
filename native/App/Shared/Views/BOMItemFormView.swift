// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

private let kBOMCategories = [
    "resistor", "capacitor", "ic", "transistor", "diode",
    "potentiometer", "switch", "jack", "connector",
    "enclosure", "hardware", "consumable", "other"
]

public struct BOMItemFormView: View {
    @Environment(WorkshopStore.self) var store
    @Environment(\.dismiss) var dismiss

    let project: Project

    @State private var form = BOMItemForm()
    @State private var saving = false
    @State private var linkSearch = ""

    public init(project: Project) {
        self.project = project
    }

    public var body: some View {
        NavigationStack {
            Form {
                // ── BOM Item fields ───────────────────────────────────────
                Section("BOM Item") {
                    TextField("Reference (e.g. R1, C3, IC1…)", text: $form.reference)
                    Picker("Category", selection: $form.category) {
                        ForEach(kBOMCategories, id: \.self) { cat in
                            Text(cat.capitalized).tag(cat)
                        }
                    }
                    TextField("Value (required)", text: $form.value)
                    Stepper("Quantity: \(form.quantity)", value: $form.quantity, in: 1...9999)
                    Toggle("Optional component", isOn: $form.isOptional)
                }

                Section("Notes") {
                    TextField("Notes", text: $form.notes)
                }

                // ── Inventory link status ─────────────────────────────────
                Section("Link to Inventory") {
                    if let cid = form.componentId,
                       let comp = store.components.first(where: { $0.id == cid }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(comp.value)
                                    .font(.system(.body, design: .monospaced))
                                    .foregroundStyle(.green)
                                Text(comp.category).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text("\(comp.quantity) in stock")
                                .font(.caption2)
                                .foregroundStyle(comp.isLowStock ? .orange : .secondary)
                            Button("Clear") { form.componentId = nil; linkSearch = "" }
                                .buttonStyle(.borderless).foregroundStyle(.red)
                        }
                    } else {
                        // Search field — results appear only when there is text
                        TextField("Search inventory…", text: $linkSearch)
                            .autocorrectionDisabled()
                    }
                }

                // ── Results: only shown while search field has text ────────
                if !linkSearch.isEmpty {
                    Section("Matches (\(filteredLinkComponents.count))") {
                        if filteredLinkComponents.isEmpty {
                            Text("No matching components")
                                .foregroundStyle(.secondary).font(.caption)
                        } else {
                            ForEach(filteredLinkComponents.prefix(20)) { comp in
                                Button {
                                    form.componentId = comp.id
                                    form.category    = comp.category
                                    if form.value.isEmpty { form.value = comp.value }
                                    linkSearch = ""          // collapse results after selection
                                } label: {
                                    HStack {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(comp.value)
                                                .font(.system(.body, design: .monospaced))
                                                .foregroundStyle(.primary)
                                            Text(comp.category)
                                                .font(.caption).foregroundStyle(.secondary)
                                        }
                                        Spacer()
                                        Text("×\(comp.quantity)")
                                            .font(.caption2)
                                            .foregroundStyle(comp.isLowStock ? .orange : .secondary)
                                    }
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Add BOM Item to \(project.name)")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") { save() }
                        .disabled(form.value.trimmingCharacters(in: .whitespaces).isEmpty || saving)
                }
            }
        }
    }

    private var filteredLinkComponents: [Component] {
        let q = linkSearch.lowercased()
        return store.components.filter {
            $0.value.lowercased().contains(q) ||
            $0.category.lowercased().contains(q) ||
            ($0.description?.lowercased().contains(q) ?? false)
        }
    }

    private func save() {
        saving = true
        Task {
            await store.addBOMItem(form, to: project)
            dismiss()
        }
    }
}
