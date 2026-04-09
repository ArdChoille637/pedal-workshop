// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

// MARK: - BuildAnalyzer

/// Classifies projects into three readiness tiers based on BOM vs on-hand inventory.
///
/// The analyser runs entirely in-memory — no network or server calls are made.
/// All matching is performed against a ``StockKey`` (category + normalised value),
/// so minor formatting differences in supplier data or user input do not cause
/// false "missing" results.
///
/// ## Tier Definitions
/// | Tier | Missing-part count | Array |
/// |------|--------------------|-------|
/// | Ready | 0 | ``BuildTiers/ready`` |
/// | ARNA 1–3 | 1–3 | ``BuildTiers/arna13`` |
/// | ARNA 4+ | 4 or more | ``BuildTiers/arna4Plus`` |
///
/// > **To change tier thresholds:** Locate the `switch missing.count` block in
/// > ``analyze(projects:bomItems:components:)`` and adjust the `case 1...3:` range.
/// > The ARNA 1–3 / ARNA 4+ boundary is that upper bound (currently `3`).
public struct BuildAnalyzer: Sendable {

    // MARK: - Public entry points

    /// Analyses buildability for every project and returns projects sorted into tiers.
    ///
    /// - Parameters:
    ///   - projects: All projects to evaluate.
    ///   - bomItems: Every BOM row across all projects; rows are filtered by `projectId` internally.
    ///   - components: Current on-hand stock. Each component's `category` + `value` are
    ///     normalised before matching so that, e.g., `"10K Ohm"` and `"10k"` resolve to the
    ///     same ``StockKey``.
    /// - Returns: A ``BuildTiers`` value grouping projects by readiness.
    public static func analyze(
        projects: [Project],
        bomItems: [BOMItem],
        components: [Component]
    ) -> BuildTiers {
        // Build a stock lookup keyed on normalised (category, value) pairs.
        var stock: [StockKey: Int] = [:]
        for c in components {
            let key = StockKey(
                category: normalizeValue(c.category),
                value:    normalizeValue(c.value)
            )
            stock[key, default: 0] += c.quantity
        }

        return classifyProjects(
            projects:  projects,
            bomItems:  bomItems,
            stock:     stock,
            listings:  nil
        )
    }

    /// Analyses buildability **and** annotates each missing part with its cheapest known
    /// source from the provided supplier listings.
    ///
    /// Use this overload when you have already fetched ``SupplierSearchResult`` values (e.g.
    /// from ``SupplierSearchService/searchAll(query:mouserKey:)``), so that the returned
    /// ``MissingPart/cheapestSource`` field is populated and an ``ProjectBuildStatus/estimatedCost``
    /// total is calculated for each project.
    ///
    /// - Parameters:
    ///   - projects: All projects to evaluate.
    ///   - bomItems: Every BOM row across all projects.
    ///   - components: Current on-hand stock.
    ///   - listings: Supplier search results keyed by the BOM item `value` string (after
    ///     normalisation). Only in-stock results contribute to the cheapest-source selection.
    ///     Pass an empty dictionary to skip cost annotation.
    /// - Returns: A ``BuildTiers`` value with cost information filled in where available.
    public static func analyze(
        projects: [Project],
        bomItems: [BOMItem],
        components: [Component],
        listings: [String: [SupplierSearchResult]]
    ) -> BuildTiers {
        var stock: [StockKey: Int] = [:]
        for c in components {
            let key = StockKey(
                category: normalizeValue(c.category),
                value:    normalizeValue(c.value)
            )
            stock[key, default: 0] += c.quantity
        }

        return classifyProjects(
            projects:  projects,
            bomItems:  bomItems,
            stock:     stock,
            listings:  listings
        )
    }

    // MARK: - Summary

    /// Derives a flat ``DashboardSummary`` from already-computed tiers.
    ///
    /// This is a pure reduction — call it after ``analyze(projects:bomItems:components:)``
    /// rather than recomputing tiers inline.
    ///
    /// - Parameters:
    ///   - components: Full component inventory (used for total quantity and low-stock counts).
    ///   - projects: All projects (used for the total project count).
    ///   - tiers: Pre-computed tier output from one of the `analyze` overloads.
    /// - Returns: A populated ``DashboardSummary`` ready for display.
    public static func summary(
        components: [Component],
        projects: [Project],
        tiers: BuildTiers
    ) -> DashboardSummary {
        let total    = components.reduce(0) { $0 + $1.quantity }
        let lowStock = components.filter(\.isLowStock).count
        return DashboardSummary(
            totalComponents:  total,
            totalUniqueParts: components.count,
            totalProjects:    projects.count,
            activeBuilds:     0,
            lowStockCount:    lowStock,
            readyToBuild:     tiers.ready.count,
            arna13:           tiers.arna13.count,
            arna4Plus:        tiers.arna4Plus.count
        )
    }

    // MARK: - Value normalisation

    /// Canonicalises a component value string so that superficially different representations
    /// of the same part produce an identical ``StockKey``.
    ///
    /// Transformations applied (in order):
    /// 1. Strip leading/trailing whitespace (handles copy-paste artefacts from datasheets).
    /// 2. Lowercase the entire string.
    /// 3. Remove the word `"ohm"` / `"ohms"` with optional surrounding space, so that
    ///    `"10k ohm"`, `"10K Ohm"`, and `"10k"` all become `"10k"`.
    /// 4. Remove a bare `"r"` suffix that some resistor shorthands append (e.g. `"470r"` →
    ///    `"470r"` is already fine; this step is a no-op for canonical forms but strips
    ///    artefacts like `"4.7kr"` → `"4.7k"`).
    ///
    /// The function is intentionally conservative — it does not attempt to convert between
    /// `"10000"`, `"10k"`, and `"10 kΩ"` because those conversions require unit parsing.
    /// Add a dedicated numeric normaliser if your data set contains mixed numeric/shorthand values.
    ///
    /// - Parameter raw: The raw string from a BOM row or component record.
    /// - Returns: A normalised string suitable for use in a ``StockKey``.
    static func normalizeValue(_ raw: String) -> String {
        var s = raw.trimmingCharacters(in: .whitespaces).lowercased()

        // Remove " ohms" / " ohm" (with optional preceding space).
        // e.g. "10k ohm" → "10k", "470 ohms" → "470"
        s = s.replacingOccurrences(
            of: #"\s*ohms?\b"#,
            with: "",
            options: .regularExpression
        )

        // Strip a stray trailing "r" that is not part of a multiplier suffix.
        // Multiplier suffixes to keep: k, m, u, n, p, f, h (inductance), v, a.
        // "470r" is idiomatic and should stay; "4.7kr" is a typo and becomes "4.7k".
        // Pattern: trailing 'r' only when preceded by a multiplier letter.
        s = s.replacingOccurrences(
            of: #"([kmunpfhva])r$"#,
            with: "$1",
            options: .regularExpression
        )

        return s
    }

    // MARK: - Private helpers

    /// Shared classification logic used by both public `analyze` overloads.
    ///
    /// - Parameters:
    ///   - projects: Projects to classify.
    ///   - bomItems: All BOM rows (will be filtered per project).
    ///   - stock: Pre-built normalised stock lookup.
    ///   - listings: Optional supplier listings dictionary; `nil` disables cost annotation.
    private static func classifyProjects(
        projects: [Project],
        bomItems: [BOMItem],
        stock: [StockKey: Int],
        listings: [String: [SupplierSearchResult]]?
    ) -> BuildTiers {
        var ready:  [ProjectBuildStatus] = []
        var arna13: [ProjectBuildStatus] = []
        var arna4p: [ProjectBuildStatus] = []

        for project in projects {
            let bom = bomItems.filter { $0.projectId == project.id }
            // Projects with no BOM rows are skipped — they cannot be classified.
            if bom.isEmpty { continue }

            var missing: [MissingPart] = []

            for item in bom {
                let key = StockKey(
                    category: normalizeValue(item.category),
                    value:    normalizeValue(item.value)
                )
                let onHand   = stock[key] ?? 0
                let shortfall = max(0, item.quantity - onHand)
                guard shortfall > 0 else { continue }

                // Attempt to find the cheapest in-stock listing for this part.
                let cheapest: CheapestSource? = listings.flatMap { dict in
                    let normVal = normalizeValue(item.value)
                    let candidates = (dict[normVal] ?? []).filter(\.inStock)
                    guard let best = candidates.min(by: { $0.price < $1.price }) else {
                        return nil
                    }
                    return CheapestSource(
                        supplier: best.supplierName,
                        price:    best.price,
                        inStock:  true
                    )
                }

                missing.append(MissingPart(
                    bomItemId:     item.id,
                    reference:     item.reference,
                    category:      item.category,
                    value:         item.value,
                    shortfall:     shortfall,
                    cheapestSource: cheapest
                ))
            }

            // Sum unit prices × shortfall quantities to produce a rough restock cost.
            let estimatedCost: Double? = {
                guard listings != nil else { return nil }
                let total = missing.reduce(0.0) { acc, part in
                    let unitPrice = part.cheapestSource?.price ?? 0
                    return acc + unitPrice * Double(part.shortfall)
                }
                return total > 0 ? total : nil
            }()

            let status = ProjectBuildStatus(
                projectId:     project.id,
                projectName:   project.name,
                effectType:    project.effectType,
                status:        project.status,
                bomCount:      bom.count,
                missingCount:  missing.count,
                missingParts:  missing,
                estimatedCost: estimatedCost
            )

            // ── Tier assignment ────────────────────────────────────────────────────────
            // TO CHANGE TIER THRESHOLDS:
            //   • The ARNA 1–3 / ARNA 4+ boundary is the upper bound of `case 1...3:`.
            //     Change `3` to a higher number to make the "nearly ready" bucket wider.
            //   • The Ready / ARNA boundary is fixed at 0 missing parts (case 0).
            switch missing.count {
            case 0:
                // ── Ready ─────────────────────────────────────────────────────────────
                // Every BOM line is fully covered by on-hand stock.
                // This project can be started immediately without ordering parts.
                ready.append(status)

            case 1...3:
                // ── ARNA 1–3 (Almost Ready, Needs A Few) ──────────────────────────────
                // A small number of parts are missing. These projects are strong candidates
                // for the next supplier order; a single small purchase unlocks the build.
                // ARNA 1–3 boundary: upper bound is 3. Adjust here if needed.
                arna13.append(status)

            default:
                // ── ARNA 4+ ───────────────────────────────────────────────────────────
                // Four or more parts are missing. The build requires a more substantial
                // restock before it can proceed. Lower-priority for near-term scheduling.
                arna4p.append(status)
            }
        }

        return BuildTiers(ready: ready, arna13: arna13, arna4Plus: arna4p)
    }
}

// MARK: - StockKey

/// A normalised composite key used to match BOM lines against on-hand inventory.
///
/// Both fields are lowercased and run through ``BuildAnalyzer/normalizeValue(_:)``
/// before the key is constructed, so that minor formatting differences in supplier
/// data or user entry do not produce false mismatches.
///
/// Example equivalent keys:
/// ```
/// StockKey(category: "resistor", value: "10k ohm")
/// StockKey(category: "Resistor", value: "10K")   // same after normalisation
/// ```
private struct StockKey: Hashable {
    /// Normalised component category (e.g. `"resistor"`, `"capacitor"`).
    let category: String
    /// Normalised component value (e.g. `"10k"`, `"100n"`, `"1n4148"`).
    let value: String
}
