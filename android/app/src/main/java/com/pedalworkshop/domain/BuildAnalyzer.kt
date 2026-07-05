// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
//
// BuildAnalyzer — reimplements the macOS WorkshopCore BuildAnalyzer and the
// shared PORT-SPEC algorithm EXACTLY so tier classification is identical across
// the Flet, macOS and Android ports. Runs entirely in-memory; no network.

package com.pedalworkshop.domain

import com.pedalworkshop.data.BOMItem
import com.pedalworkshop.data.Component
import com.pedalworkshop.data.Project
import com.pedalworkshop.data.SearchResult

object BuildAnalyzer {

    // Precompiled regexes (order matches the spec).
    private val OHM_RE = Regex("""\s*ohms?\b""")
    private val EURO_SHORTHAND_RE = Regex("""^(\d+)([kmunpf])(\d+)$""")
    private val TRAILING_R_AFTER_MULT_RE = Regex("""([kmunpfhva])r$""")
    private val BARE_R_RE = Regex("""^(\d+(?:\.\d+)?)r$""")

    /**
     * Canonicalises a value/category string so superficially different forms
     * (e.g. "10K Ohm" and "10k") produce the same StockKey.
     *
     * Steps (EXACT, in order):
     *  1. trim whitespace; lowercase.
     *  2. replace unicode ohm signs (U+2126, U+03C9, U+03A9) with "ohm".
     *  3. remove `\s*ohms?\b` → "".
     *  4. European shorthand `^(\d+)([kmunpf])(\d+)$` → `$1.$3$2` (4k7 → 4.7k).
     *  5. `([kmunpfhva])r$` → `$1` (strip stray trailing r after a multiplier).
     *  6. `^(\d+(?:\.\d+)?)r$` → `$1` (bare "470r" → "470").
     */
    fun normalizeValue(raw: String): String {
        // 1. trim + lowercase.  2. Unicode ohm signs → the word "ohm".
        s = s.replace('Ω', 'o') // (unused placeholder removed below)
        s = raw.trim().lowercase()
            .replace("Ω", "ohm") // Ω OHM SIGN
            .replace("ω", "ohm") // ω greek small omega
            .replace("Ω", "ohm") // Ω greek capital omega

        // 3. remove " ohm"/" ohms" with optional preceding whitespace.
        s = OHM_RE.replace(s, "")

        // 4. European embedded-multiplier shorthand ("4k7" → "4.7k").
        s = EURO_SHORTHAND_RE.replace(s) { m ->
            "${m.groupValues[1]}.${m.groupValues[3]}${m.groupValues[2]}"
        }

        // 5. strip a stray trailing "r" after a multiplier ("4.7kr" → "4.7k").
        s = TRAILING_R_AFTER_MULT_RE.replace(s) { m -> m.groupValues[1] }

        // 6. bare trailing "r" on a plain number ("470r" → "470").
        s = BARE_R_RE.replace(s) { m -> m.groupValues[1] }

        return s
    }

    /**
     * Classify all projects into readiness tiers.
     *
     * @param listings Optional Mouser results keyed by normalized value; when
     *   supplied, missing parts are annotated with their cheapest in-stock
     *   source and each project gets an estimated restock cost.
     */
    fun analyze(
        projects: List<Project>,
        bomItems: List<BOMItem>,
        components: List<Component>,
        listings: Map<String, List<SearchResult>>? = null,
    ): BuildTiers {
        // Build on-hand stock lookup keyed on normalized (category, value).
        val stock = HashMap<StockKey, Int>()
        for (c in components) {
            val key = StockKey(normalizeValue(c.category), normalizeValue(c.value))
            stock[key] = (stock[key] ?: 0) + c.quantity
        }

        val ready = ArrayList<ProjectBuildStatus>()
        val arna13 = ArrayList<ProjectBuildStatus>()
        val arna4p = ArrayList<ProjectBuildStatus>()

        for (project in projects) {
            val bom = bomItems.filter { it.projectId == project.id }
            if (bom.isEmpty()) continue // unclassifiable — skip

            // Optional rows AND the enclosure never count toward the ARNA total.
            val required = bom.filter {
                it.isOptional == 0 &&
                    it.category.trim().lowercase() != "enclosure"
            }

            // Aggregate demand per normalized key; keep first row as representative
            // so duplicate BOM lines can't each claim the full on-hand quantity.
            val demand = LinkedHashMap<StockKey, Int>()
            val representative = HashMap<StockKey, BOMItem>()
            for (item in required) {
                val key = StockKey(normalizeValue(item.category), normalizeValue(item.value))
                demand[key] = (demand[key] ?: 0) + item.quantity
                if (!representative.containsKey(key)) representative[key] = item
            }

            val missing = ArrayList<MissingPart>()

            // Stable iteration order (sort by category then value).
            val orderedKeys = demand.keys.sortedWith(
                compareBy({ it.category }, { it.value })
            )
            for (key in orderedKeys) {
                val needed = demand[key] ?: continue
                val item = representative[key] ?: continue
                val onHand = stock[key] ?: 0
                val shortfall = maxOf(0, needed - onHand)
                if (shortfall <= 0) continue

                // Cheapest in-stock listing for this part, if listings supplied.
                val cheapest: CheapestSource? = listings?.let { dict ->
                    val normVal = normalizeValue(item.value)
                    val candidates = (dict[normVal] ?: emptyList()).filter { it.inStock }
                    candidates.minByOrNull { it.price }?.let { best ->
                        CheapestSource(best.supplierName, best.price, true)
                    }
                }

                missing.add(
                    MissingPart(
                        bomItemId = item.id,
                        reference = item.reference,
                        category = item.category,
                        value = item.value,
                        shortfall = shortfall,
                        cheapestSource = cheapest,
                    )
                )
            }

            val estimatedCost: Double? = if (listings == null) {
                null
            } else {
                val total = missing.sumOf { part ->
                    (part.cheapestSource?.price ?: 0.0) * part.shortfall
                }
                if (total > 0) total else null
            }

            val status = ProjectBuildStatus(
                projectId = project.id,
                projectName = project.name,
                effectType = project.effectType,
                status = project.status,
                bomCount = bom.size,
                missingCount = missing.size,
                missingParts = missing,
                estimatedCost = estimatedCost,
            )

            when (missing.size) {
                0 -> ready.add(status)
                in 1..3 -> arna13.add(status)
                else -> arna4p.add(status)
            }
        }

        return BuildTiers(ready = ready, arna13 = arna13, arna4Plus = arna4p)
    }

    /** Derive the flat dashboard summary from already-computed tiers. */
    fun summary(
        components: List<Component>,
        projects: List<Project>,
        tiers: BuildTiers,
    ): DashboardSummary {
        val total = components.sumOf { it.quantity }
        val lowStock = components.count { it.isLowStock }
        val activeStatuses = setOf("prototype", "production")
        val active = projects.count { it.status in activeStatuses }
        return DashboardSummary(
            totalComponents = total,
            totalUniqueParts = components.size,
            totalProjects = projects.size,
            activeBuilds = active,
            lowStockCount = lowStock,
            readyToBuild = tiers.ready.size,
            arna13 = tiers.arna13.size,
            arna4Plus = tiers.arna4Plus.size,
        )
    }
}
