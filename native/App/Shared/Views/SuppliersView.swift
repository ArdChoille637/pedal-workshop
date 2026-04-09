import SwiftUI
import WorkshopCore

public struct SuppliersView: View {
    @Environment(WorkshopStore.self) var store

    public init() {}

    var totalListings: Int { store.supplierListings.count }

    public var body: some View {
        List(store.suppliers) { supplier in
            SupplierRow(supplier: supplier,
                        listings: store.supplierListings.filter { $0.supplierId == supplier.id })
        }
        .navigationTitle("Suppliers")
        .refreshable { await store.loadSuppliers() }
        .task { if store.suppliers.isEmpty { await store.loadSuppliers() } }
        .safeAreaInset(edge: .bottom) {
            if totalListings > 0 {
                HStack {
                    Image(systemName: "tag.fill").foregroundStyle(.secondary)
                    Text("\(totalListings) price links across \(store.supplierListings.map(\.supplierId).uniqued().count) suppliers")
                        .font(.caption).foregroundStyle(.secondary)
                }
                .padding(10)
                .background(.bar)
            }
        }
    }
}

struct SupplierRow: View {
    let supplier: Supplier
    let listings: [SupplierListing]

    var apiTypeColor: Color {
        supplier.apiType == "api" ? .green : .yellow
    }

    var lastPolled: String {
        guard let ts = supplier.lastPolledAt else { return "Never polled" }
        return "Polled: \(ts.prefix(10))"
    }

    var cheapest: SupplierListing? {
        listings.filter(\.inStock).min(by: { $0.price < $1.price })
    }

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(supplier.pollEnabled == 1 ? Color.green : Color.gray)
                .frame(width: 10, height: 10)

            VStack(alignment: .leading, spacing: 4) {
                Text(supplier.name).font(.headline)
                if let url = supplier.website {
                    Text(url).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                }
                if !listings.isEmpty {
                    Text("\(listings.count) linked price\(listings.count == 1 ? "" : "s")")
                        .font(.caption2).foregroundStyle(.tertiary)
                } else {
                    Text(lastPolled).font(.caption2).foregroundStyle(.tertiary)
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(supplier.apiType.uppercased())
                    .font(.caption2).padding(.horizontal, 6).padding(.vertical, 2)
                    .background(apiTypeColor.opacity(0.15))
                    .foregroundStyle(apiTypeColor)
                    .clipShape(Capsule())

                if let listing = cheapest {
                    Text("Best \(String(format: "$%.2f", listing.price))")
                        .font(.caption2)
                        .foregroundStyle(.green)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

// Small helper to unique an array of Hashable
private extension Array where Element: Hashable {
    func uniqued() -> [Element] { Array(Set(self)) }
}
