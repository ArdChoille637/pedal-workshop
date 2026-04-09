import SwiftUI
import WorkshopCore

public struct DashboardView: View {
    @Environment(WorkshopStore.self) var store

    public init() {}

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                if let s = store.summary {
                    summaryGrid(s)
                }
                if let tiers = store.buildTiers {
                    tierSection("✅  Ready to Build", items: tiers.ready, color: .green)
                    tierSection("⚠️  ARNA 1–3 Parts", items: tiers.arna13, color: .yellow)
                    tierSection("🔴  ARNA 4+ Parts",  items: tiers.arna4Plus, color: .red)
                }
                if store.summary == nil && store.buildTiers == nil {
                    if store.isLoading {
                        ProgressView("Loading dashboard…")
                            .frame(maxWidth: .infinity)
                    } else {
                        VStack(spacing: 12) {
                            ContentUnavailableView(
                                "No Data",
                                systemImage: "tray",
                                description: Text("Pull down to refresh or tap Reload.")
                            )
                            if let err = store.error {
                                Text(err)
                                    .font(.caption).foregroundStyle(.red)
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal)
                            }
                            Button("Reload") { Task { await store.loadAll() } }
                                .buttonStyle(.borderedProminent)
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle("Dashboard")
        .refreshable { await store.loadAll() }
        .task { if store.summary == nil { await store.loadAll() } }
    }

    @ViewBuilder
    private func summaryGrid(_ s: DashboardSummary) -> some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 140))], spacing: 12) {
            StatCard(value: s.totalComponents,  label: "Parts on Hand",  color: .blue)
            StatCard(value: s.totalUniqueParts, label: "Unique Parts",   color: .purple)
            StatCard(value: s.totalProjects,    label: "Projects",       color: .indigo)
            StatCard(value: s.activeBuilds,     label: "Active Builds",  color: .green)
            StatCard(value: s.readyToBuild,     label: "Ready to Build", color: .mint)
            StatCard(value: s.lowStockCount,    label: "Low Stock",      color: s.lowStockCount > 0 ? .orange : .gray)
        }
    }

    @ViewBuilder
    private func tierSection(_ title: String, items: [ProjectBuildStatus], color: Color) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .foregroundStyle(color)
                .padding(.bottom, 2)

            if items.isEmpty {
                Text("No projects in this tier")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.leading, 4)
            } else {
                ForEach(items) { project in
                    ProjectTierRow(project: project)
                }
            }
        }
    }
}

struct StatCard: View {
    let value: Int
    let label: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("\(value)")
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundStyle(color)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background.secondary)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct ProjectTierRow: View {
    let project: ProjectBuildStatus

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(project.projectName)
                    .font(.subheadline).fontWeight(.semibold)
                if let et = project.effectType {
                    Text(et)
                        .font(.caption2)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(Color.indigo.opacity(0.15))
                        .foregroundStyle(.indigo)
                        .clipShape(Capsule())
                }
                Spacer()
                Text("\(project.bomCount) parts")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if !project.missingParts.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        ForEach(project.missingParts) { part in
                            HStack(spacing: 3) {
                                if let ref = part.reference { Text(ref + ":").font(.caption2).foregroundStyle(.secondary) }
                                Text(part.value).font(.caption2).fontWeight(.medium)
                                Text("×\(part.shortfall)").font(.caption2).foregroundStyle(.secondary)
                            }
                            .padding(.horizontal, 6).padding(.vertical, 3)
                            .background(Color.red.opacity(0.1))
                            .foregroundStyle(.red)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                        }
                    }
                }
                if let cost = project.estimatedCost, cost > 0 {
                    Text("Est. acquisition: $\(String(format: "%.2f", cost))")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .padding(10)
        .background(.background.secondary)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}
