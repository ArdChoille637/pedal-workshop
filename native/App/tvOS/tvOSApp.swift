import SwiftUI
import WorkshopCore

@main
struct tvOSApp: App {
    @State private var store = WorkshopStore.shared

    var body: some Scene {
        WindowGroup {
            TVContentView()
                .environment(store)
        }
    }
}

struct TVContentView: View {
    var body: some View {
        TabView {
            NavigationStack { TVDashboardView() }
                .tabItem { Label("Dashboard", systemImage: "square.grid.2x2") }
            NavigationStack { TVInventoryView() }
                .tabItem { Label("Inventory", systemImage: "cube.box") }
            NavigationStack { ProjectsView() }
                .tabItem { Label("Projects", systemImage: "folder") }
            NavigationStack { SchematicsView() }
                .tabItem { Label("Schematics", systemImage: "doc.text.image") }
        }
    }
}

// TV-optimized Dashboard — large text, focus-friendly cards
struct TVDashboardView: View {
    @Environment(WorkshopStore.self) var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 40) {
                if let s = store.summary {
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4), spacing: 20) {
                        TVStatCard(value: s.totalComponents,  label: "Parts on Hand",  color: .blue)
                        TVStatCard(value: s.readyToBuild,     label: "Ready to Build", color: .green)
                        TVStatCard(value: s.arna13,           label: "ARNA 1–3",       color: .yellow)
                        TVStatCard(value: s.lowStockCount,    label: "Low Stock",      color: .orange)
                    }
                }
                if let tiers = store.buildTiers, !tiers.ready.isEmpty {
                    Text("Ready to Build").font(.title2).fontWeight(.semibold)
                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 20) {
                        ForEach(tiers.ready) { p in
                            TVProjectCard(project: p)
                        }
                    }
                }
            }
            .padding(60)
        }
        .navigationTitle("Pedal Workshop")
        .task { await store.loadAll() }
    }
}

struct TVStatCard: View {
    let value: Int; let label: String; let color: Color
    var body: some View {
        VStack(spacing: 8) {
            Text("\(value)").font(.system(size: 64, weight: .bold, design: .rounded)).foregroundStyle(color)
            Text(label).font(.callout).foregroundStyle(.secondary)
        }
        .padding(30).frame(maxWidth: .infinity)
        .background(.regularMaterial).clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct TVProjectCard: View {
    let project: ProjectBuildStatus
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(project.projectName).font(.headline).lineLimit(2)
            if let et = project.effectType { Text(et).font(.caption).foregroundStyle(.indigo) }
            Text("\(project.bomCount) parts").font(.caption).foregroundStyle(.secondary)
        }
        .padding(24).frame(maxWidth: .infinity, alignment: .leading)
        .background(.regularMaterial).clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// TV Inventory — large focusable list
struct TVInventoryView: View {
    @Environment(WorkshopStore.self) var store

    var body: some View {
        List(store.components) { c in
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(c.value).font(.system(.title3, design: .monospaced)).fontWeight(.semibold)
                    Text(c.category).font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
                Text("\(c.quantity)")
                    .font(.system(size: 40, weight: .bold, design: .rounded))
                    .foregroundStyle(c.isLowStock ? .orange : .primary)
            }
            .padding(.vertical, 8)
        }
        .navigationTitle("Inventory")
        .task { await store.loadComponents() }
    }
}
