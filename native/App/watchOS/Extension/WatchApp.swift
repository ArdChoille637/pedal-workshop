import SwiftUI
import WorkshopCore

@main
struct WatchApp: App {
    @State private var store = WorkshopStore.shared

    var body: some Scene {
        WindowGroup {
            WatchContentView()
                .environment(store)
        }
    }
}

struct WatchContentView: View {
    @Environment(WorkshopStore.self) var store

    var body: some View {
        NavigationStack {
            List {
                // Summary section
                Section {
                    if let s = store.summary {
                        WatchStatRow(label: "Ready",     value: s.readyToBuild, color: .green)
                        WatchStatRow(label: "ARNA 1–3",  value: s.arna13,       color: .yellow)
                        WatchStatRow(label: "ARNA 4+",   value: s.arna4Plus,    color: .red)
                        WatchStatRow(label: "Low Stock",  value: s.lowStockCount, color: .orange)
                    } else {
                        ProgressView()
                    }
                } header: { Text("Dashboard") }

                // Ready to build list
                if let tiers = store.buildTiers, !tiers.ready.isEmpty {
                    Section {
                        ForEach(tiers.ready) { p in
                            Text(p.projectName).font(.caption2)
                        }
                    } header: { Text("Ready") }
                }

                // Low stock
                if !store.lowStockComponents.isEmpty {
                    Section {
                        ForEach(store.lowStockComponents.prefix(5)) { c in
                            HStack {
                                Text(c.value).font(.caption2)
                                Spacer()
                                Text("\(c.quantity)").font(.caption2).foregroundStyle(.orange)
                            }
                        }
                    } header: { Text("⚠ Low Stock") }
                }
            }
            .navigationTitle("Workshop")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { await store.loadAll() }
    }
}

struct WatchStatRow: View {
    let label: String
    let value: Int
    let color: Color

    var body: some View {
        HStack {
            Text(label).font(.caption2)
            Spacer()
            Text("\(value)")
                .font(.system(.body, design: .rounded).weight(.bold))
                .foregroundStyle(color)
        }
    }
}
