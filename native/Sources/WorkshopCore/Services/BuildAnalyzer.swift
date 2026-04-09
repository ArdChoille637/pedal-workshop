import Foundation

/// Classifies projects into 3 readiness tiers based on BOM vs on-hand inventory.
/// Runs entirely in-memory — no server required.
public struct BuildAnalyzer: Sendable {

    // MARK: – Public entry point

    public static func analyze(
        projects: [Project],
        bomItems: [BOMItem],
        components: [Component]
    ) -> BuildTiers {
        // Build a lookup: (category, value) → on-hand quantity
        var stock: [StockKey: Int] = [:]
        for c in components {
            let key = StockKey(category: c.category.lowercased(), value: c.value.lowercased())
            stock[key, default: 0] += c.quantity
        }

        var ready:   [ProjectBuildStatus] = []
        var arna13:  [ProjectBuildStatus] = []
        var arna4p:  [ProjectBuildStatus] = []

        for project in projects {
            let bom = bomItems.filter { $0.projectId == project.id }
            if bom.isEmpty { continue }

            var missing: [MissingPart] = []
            for item in bom {
                let key = StockKey(category: item.category.lowercased(), value: item.value.lowercased())
                let onHand = stock[key] ?? 0
                let shortfall = max(0, item.quantity - onHand)
                if shortfall > 0 {
                    missing.append(MissingPart(
                        bomItemId: item.id,
                        reference: item.reference,
                        category: item.category,
                        value: item.value,
                        shortfall: shortfall,
                        cheapestSource: nil
                    ))
                }
            }

            let status = ProjectBuildStatus(
                projectId: project.id,
                projectName: project.name,
                effectType: project.effectType,
                status: project.status,
                bomCount: bom.count,
                missingCount: missing.count,
                missingParts: missing,
                estimatedCost: nil
            )

            switch missing.count {
            case 0:        ready.append(status)
            case 1...3:    arna13.append(status)
            default:       arna4p.append(status)
            }
        }

        return BuildTiers(ready: ready, arna13: arna13, arna4Plus: arna4p)
    }

    // MARK: – Summary from tiers

    public static func summary(
        components: [Component],
        projects: [Project],
        tiers: BuildTiers
    ) -> DashboardSummary {
        let total = components.reduce(0) { $0 + $1.quantity }
        let lowStock = components.filter(\.isLowStock).count
        return DashboardSummary(
            totalComponents: total,
            totalUniqueParts: components.count,
            totalProjects: projects.count,
            activeBuilds: 0,
            lowStockCount: lowStock,
            readyToBuild: tiers.ready.count,
            arna13: tiers.arna13.count,
            arna4Plus: tiers.arna4Plus.count
        )
    }
}

// MARK: – Helpers

private struct StockKey: Hashable {
    let category: String
    let value: String
}
