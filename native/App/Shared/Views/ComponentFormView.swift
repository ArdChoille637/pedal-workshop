// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

private let kCategories = [
    "resistor", "capacitor", "ic", "transistor", "diode",
    "potentiometer", "switch", "jack", "connector",
    "enclosure", "hardware", "consumable", "other"
]

public struct ComponentFormView: View {
    @Environment(WorkshopStore.self) var store
    @Environment(\.dismiss) var dismiss

    let editing: Component?

    @State private var form: ComponentForm
    @State private var saving = false
    @State private var errorMessage: String?

    // Add mode
    public init() {
        editing = nil
        _form = State(initialValue: ComponentForm())
    }

    // Edit mode
    public init(editing component: Component) {
        editing = component
        _form = State(initialValue: ComponentForm(from: component))
    }

    // Pre-fill from a scanned barcode
    init(fromBarcode barcode: ParsedBarcode) {
        editing = nil
        var f = ComponentForm()
        f.mpn   = barcode.mpn ?? barcode.supplierPN ?? ""
        f.value = barcode.mpn ?? ""
        if let spn = barcode.supplierPN {
            f.notes = "Supplier PN: \(spn)"
        }
        _form = State(initialValue: f)
    }

    public var body: some View {
        NavigationStack {
            Form {
                // Identity
                Section("Identity") {
                    Picker("Category", selection: $form.category) {
                        ForEach(kCategories, id: \.self) { cat in
                            Text(cat.capitalized).tag(cat)
                        }
                    }
                    TextField("Value (e.g. 10k, 100nF)", text: $form.value)
                    TextField("Package (e.g. 0805, TO-92)", text: $form.package)
                }

                // Detail
                Section("Detail") {
                    TextField("Description", text: $form.description)
                    TextField("Manufacturer", text: $form.manufacturer)
                    TextField("MPN", text: $form.mpn)
                    TextField("Value unit (e.g. Ω, F, H)", text: $form.valueUnit)
                }

                // Stock
                Section("Stock") {
                    Stepper("Quantity: \(form.quantity)", value: $form.quantity, in: 0...99999)
                    Stepper("Min quantity: \(form.minQuantity)", value: $form.minQuantity, in: 0...9999)
                    TextField("Location (e.g. Bin A-12)", text: $form.location)
                }

                // Notes
                Section("Notes") {
                    TextEditor(text: $form.notes)
                        .frame(minHeight: 80)
                }

                if let msg = errorMessage {
                    Section {
                        Text(msg).foregroundStyle(.red).font(.caption)
                    }
                }
            }
            .navigationTitle(editing == nil ? "Add Component" : "Edit Component")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .disabled(form.value.trimmingCharacters(in: .whitespaces).isEmpty || saving)
                }
            }
        }
    }

    private func save() {
        saving = true
        Task {
            if let existing = editing {
                // Apply form fields back onto the existing component
                var updated = existing
                updated.category     = form.category
                updated.subcategory  = form.subcategory.nilIfEmpty
                updated.value        = form.value
                updated.valueUnit    = form.valueUnit.nilIfEmpty
                updated.package      = form.package.nilIfEmpty
                updated.description  = form.description.nilIfEmpty
                updated.manufacturer = form.manufacturer.nilIfEmpty
                updated.mpn          = form.mpn.nilIfEmpty
                updated.quantity     = form.quantity
                updated.minQuantity  = form.minQuantity
                updated.location     = form.location.nilIfEmpty
                updated.notes        = form.notes.nilIfEmpty
                await store.updateComponent(updated)
            } else {
                await store.addComponent(form)
            }
            dismiss()
        }
    }
}
