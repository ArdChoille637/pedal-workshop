// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

public struct InventoryView: View {
    @Environment(WorkshopStore.self) var store
    @State private var showingAdd     = false
    @State private var showingBarcode = false

    public init() {}

    public var body: some View {
        @Bindable var store = store
        Group {
            if store.isLoading && store.components.isEmpty {
                ProgressView("Loading inventory…").frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if store.components.isEmpty {
                ContentUnavailableView("No components", systemImage: "cube.box",
                    description: Text("Tap + to add your first component."))
            } else {
                List(filtered) { component in
                    ComponentRow(component: component)
                }
            }
        }
        .navigationTitle("Inventory (\(filtered.count))")
        .searchable(text: $store.componentSearch, prompt: "Search value, description, MPN…")
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Picker("Category", selection: $store.componentCategory) {
                    Text("All").tag("")
                    ForEach(store.componentCategories, id: \.self) { cat in
                        Text(cat.capitalized).tag(cat)
                    }
                }
                .pickerStyle(.menu)
            }
            ToolbarItem(placement: .primaryAction) {
                HStack(spacing: 4) {
                    Button {
                        showingBarcode = true
                    } label: {
                        Image(systemName: "barcode.viewfinder")
                    }
                    .help("Bulk entry via barcode scanner")
                    .keyboardShortcut("k", modifiers: .command)

                    Button {
                        showingAdd = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            ComponentFormView()
                .environment(store)
        }
        .sheet(isPresented: $showingBarcode) {
            BarcodeEntryView()
                .environment(store)
        }
        .refreshable { await store.loadComponents() }
        .task { if store.components.isEmpty { await store.loadComponents() } }
    }

    private var filtered: [Component] { store.filteredComponents }
}

struct ComponentRow: View {
    @Environment(WorkshopStore.self) var store
    let component: Component

    @State private var showingEdit = false
    @State private var showingDeleteConfirm = false
    @State private var showingPriceLookup = false

    var cheapest: SupplierListing? { store.cheapestListing(for: component) }

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(component.value)
                        .font(.system(.body, design: .monospaced)).fontWeight(.semibold)
                    Text(component.category)
                        .font(.caption2).padding(.horizontal, 5).padding(.vertical, 2)
                        .background(Color.secondary.opacity(0.15))
                        .clipShape(Capsule())
                }
                if let desc = component.description {
                    Text(desc).font(.caption).foregroundStyle(.secondary)
                }
                if let loc = component.location {
                    Label(loc, systemImage: "mappin.circle").font(.caption2).foregroundStyle(.tertiary)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text("\(component.quantity)")
                    .font(.system(size: 22, weight: .bold, design: .rounded))
                    .foregroundStyle(component.isLowStock ? .orange : .primary)
                HStack(spacing: 4) {
                    Button {
                        Task { await store.adjustQuantity(component: component, delta: -1) }
                    } label: {
                        Image(systemName: "minus.circle")
                    }
                    .buttonStyle(.borderless).foregroundStyle(.red)

                    Button {
                        Task { await store.adjustQuantity(component: component, delta: 1) }
                    } label: {
                        Image(systemName: "plus.circle")
                    }
                    .buttonStyle(.borderless).foregroundStyle(.green)
                }
                // Best price badge
                if let listing = cheapest {
                    Text(String(format: "$%.2f", listing.price))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 4)
        .swipeActions(edge: .leading, allowsFullSwipe: false) {
            Button { showingEdit = true } label: {
                Label("Edit", systemImage: "pencil")
            }.tint(.blue)
        }
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button(role: .destructive) { showingDeleteConfirm = true } label: {
                Label("Delete", systemImage: "trash")
            }
        }
        .contextMenu {
            Button("Edit") { showingEdit = true }
            Button("Find Prices…") { showingPriceLookup = true }
            Divider()
            Button("Delete", role: .destructive) { showingDeleteConfirm = true }
        }
        .sheet(isPresented: $showingEdit) {
            ComponentFormView(editing: component)
                .environment(store)
        }
        .sheet(isPresented: $showingPriceLookup) {
            PriceLookupView(component: component)
                .environment(store)
        }
        .confirmationDialog(
            "Delete \(component.value)?",
            isPresented: $showingDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task { await store.deleteComponent(component) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will permanently remove the component from your inventory.")
        }
    }
}
