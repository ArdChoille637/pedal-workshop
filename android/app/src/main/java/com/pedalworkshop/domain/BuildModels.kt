// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
//
// Domain models produced by the BuildAnalyzer. These are transient view models,
// never persisted. They mirror the macOS WorkshopCore Dashboard models.

package com.pedalworkshop.domain

/** Key used to match BOM demand against on-hand stock (normalized category + value). */
data class StockKey(val category: String, val value: String)

/** Cheapest known in-stock source for a missing part (populated when listings supplied). */
data class CheapestSource(
    val supplier: String,
    val price: Double,
    val inStock: Boolean,
)

/** A part the project needs but doesn't have enough of on hand. */
data class MissingPart(
    val bomItemId: Int,
    val reference: String?,
    val category: String,
    val value: String,
    val shortfall: Int,
    val cheapestSource: CheapestSource? = null,
)

/** Readiness tier for a single project. */
enum class BuildTier { READY, ARNA_13, ARNA_4_PLUS }

/** Per-project build readiness result. */
data class ProjectBuildStatus(
    val projectId: Int,
    val projectName: String,
    val effectType: String?,
    val status: String,
    val bomCount: Int,
    val missingCount: Int,
    val missingParts: List<MissingPart>,
    val estimatedCost: Double? = null,
) {
    val tier: BuildTier
        get() = when (missingCount) {
            0 -> BuildTier.READY
            in 1..3 -> BuildTier.ARNA_13
            else -> BuildTier.ARNA_4_PLUS
        }
}

/** Projects grouped by readiness tier. */
data class BuildTiers(
    val ready: List<ProjectBuildStatus> = emptyList(),
    val arna13: List<ProjectBuildStatus> = emptyList(),
    val arna4Plus: List<ProjectBuildStatus> = emptyList(),
) {
    /** Flat lookup of every classified project by id. */
    fun statusFor(projectId: Int): ProjectBuildStatus? =
        (ready + arna13 + arna4Plus).firstOrNull { it.projectId == projectId }
}

/** Flat dashboard headline numbers. */
data class DashboardSummary(
    val totalComponents: Int = 0,
    val totalUniqueParts: Int = 0,
    val totalProjects: Int = 0,
    val activeBuilds: Int = 0,
    val lowStockCount: Int = 0,
    val readyToBuild: Int = 0,
    val arna13: Int = 0,
    val arna4Plus: Int = 0,
)
