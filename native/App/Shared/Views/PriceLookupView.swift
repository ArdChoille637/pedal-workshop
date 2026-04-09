import SwiftUI
import WorkshopCore

// MARK: – Price Lookup sheet

struct PriceLookupView: View {
    @Environment(WorkshopStore.self) var store
    @Environment(\.dismiss) var dismiss

    let component: Component

    @State private var query: String
    @State private var results:   [SupplierSearchResult] = []
    @State private var isLoading  = false
    @State private var errorMsg:  String?
    @State private var savedIds:  Set<String> = []   // result IDs already saved

    init(component: Component) {
        self.component = component
        // Pre-build query: value + category (e.g. "10k resistor")
        _query = State(initialValue: "\(component.value) \(component.category)")
    }

    var savedListings: [SupplierListing] { store.listingsFor(component) }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                searchBar
                Divider()
                content
            }
            .navigationTitle("Find Prices — \(component.value)")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
        .frame(minWidth: 640, minHeight: 520)
        .task { await runSearch() }
    }

    // MARK: – Search bar

    private var searchBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
            TextField("Search query…", text: $query)
                .textFieldStyle(.plain)
                .onSubmit { Task { await runSearch() } }
            if isLoading {
                ProgressView().scaleEffect(0.7)
            } else {
                Button("Search") { Task { await runSearch() } }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(query.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(12)
        .background(.background.secondary)
    }

    // MARK: – Content

    @ViewBuilder
    private var content: some View {
        if let err = errorMsg {
            Text(err).foregroundStyle(.red).font(.caption).padding()
        }

        HSplitView {
            // Left: search results
            resultsPanel

            // Right: saved listings for this component
            savedPanel
        }
    }

    // MARK: – Results panel

    private var resultsPanel: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("SEARCH RESULTS")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 12)
                .padding(.top, 10)
                .padding(.bottom, 6)

            if results.isEmpty && !isLoading {
                VStack(spacing: 8) {
                    Image(systemName: "cart.badge.questionmark")
                        .font(.title2).foregroundStyle(.secondary)
                    Text("No results")
                        .font(.subheadline).foregroundStyle(.secondary)
                    Text("Try a different search term")
                        .font(.caption).foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(results) { result in
                    PriceResultRow(result: result, isSaved: savedIds.contains(result.id)) {
                        Task { await save(result) }
                    }
                }
                .listStyle(.inset)
            }
        }
        .frame(minWidth: 360)
    }

    // MARK: – Saved panel

    private var savedPanel: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("LINKED PRICES")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()
                if let cheap = store.cheapestListing(for: component) {
                    Text("Best: \(String(format: "$%.2f", cheap.price))")
                        .font(.caption2)
                        .foregroundStyle(.green)
                }
            }
            .padding(.horizontal, 12)
            .padding(.top, 10)
            .padding(.bottom, 6)

            if savedListings.isEmpty {
                Text("Save a result to link it here.")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .padding(.horizontal, 12)
                    .frame(maxHeight: .infinity)
            } else {
                List(savedListings) { listing in
                    SavedListingRow(listing: listing, suppliers: store.suppliers) {
                        Task { await store.deleteSupplierListing(listing) }
                    }
                }
                .listStyle(.inset)
            }
        }
        .frame(width: 240)
        .background(.background.secondary)
    }

    // MARK: – Actions

    private func runSearch() async {
        guard !query.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        isLoading = true
        errorMsg  = nil
        results   = await store.searchSuppliers(query: query)
        isLoading = false
        if results.isEmpty {
            errorMsg = "No results from Tayda, Mammoth, or Love My Switches. Check your query or try a simpler term."
        }
    }

    private func save(_ result: SupplierSearchResult) async {
        await store.saveSupplierListing(result, for: component)
        savedIds.insert(result.id)
    }
}

// MARK: – Price result row

struct PriceResultRow: View {
    let result:  SupplierSearchResult
    let isSaved: Bool
    let onSave:  () -> Void

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(result.supplierName)
                        .font(.system(size: 9, weight: .bold))
                        .padding(.horizontal, 4).padding(.vertical, 2)
                        .background(supplierColor.opacity(0.12))
                        .foregroundStyle(supplierColor)
                        .clipShape(RoundedRectangle(cornerRadius: 3))
                    Text(result.sku)
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
                Text(result.title)
                    .font(.caption)
                    .lineLimit(2)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(result.priceString)
                    .font(.system(size: 15, weight: .semibold, design: .monospaced))

                HStack(spacing: 4) {
                    Circle()
                        .fill(result.inStock ? Color.green : Color.red)
                        .frame(width: 6, height: 6)
                    Text(result.inStock ? "In stock" : "Out of stock")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            HStack(spacing: 6) {
                if let url = result.url {
                    Link(destination: url) {
                        Image(systemName: "safari")
                    }
                    .buttonStyle(.borderless)
                    .help("Open in browser")
                }
                Button(action: onSave) {
                    Image(systemName: isSaved ? "checkmark.circle.fill" : "plus.circle")
                        .foregroundStyle(isSaved ? .green : .blue)
                }
                .buttonStyle(.borderless)
                .help(isSaved ? "Already saved" : "Link to component")
                .disabled(isSaved)
            }
        }
        .padding(.vertical, 3)
    }

    private var supplierColor: Color {
        switch result.supplierSlug {
        case "tayda":   return .orange
        case "mammoth": return .purple
        case "lms":     return .pink
        case "mouser":  return .blue
        default:        return .gray
        }
    }
}

// MARK: – Saved listing row

struct SavedListingRow: View {
    let listing:   SupplierListing
    let suppliers: [Supplier]
    let onDelete:  () -> Void

    var supplierName: String {
        suppliers.first(where: { $0.id == listing.supplierId })?.name ?? "Unknown"
    }

    var body: some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 3) {
                Text(supplierName)
                    .font(.caption2).foregroundStyle(.secondary)
                Text(listing.sku)
                    .font(.system(.caption, design: .monospaced))
                    .lineLimit(1)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 3) {
                Text(String(format: "$%.2f", listing.price))
                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
                Circle()
                    .fill(listing.inStock ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
            }

            HStack(spacing: 4) {
                if let urlStr = listing.url, let url = URL(string: urlStr) {
                    Link(destination: url) {
                        Image(systemName: "safari")
                    }
                    .buttonStyle(.borderless)
                }
                Button(role: .destructive, action: onDelete) {
                    Image(systemName: "minus.circle")
                }
                .buttonStyle(.borderless)
            }
        }
        .padding(.vertical, 2)
    }
}
