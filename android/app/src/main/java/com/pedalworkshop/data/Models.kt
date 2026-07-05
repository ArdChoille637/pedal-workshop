// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop
//
// Data models — mirror the macOS SwiftUI WorkshopCore models and the shared
// port spec exactly. JSON keys are snake_case (see @SerialName). Behaviour must
// stay identical across the Flet, macOS and Android ports.

package com.pedalworkshop.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** A single inventory part. */
@Serializable
data class Component(
    val id: Int = 0,
    val category: String = "",
    val subcategory: String? = null,
    val value: String = "",
    @SerialName("value_numeric") val valueNumeric: Double? = null,
    @SerialName("value_unit") val valueUnit: String? = null,
    val `package`: String? = null,
    val description: String? = null,
    val manufacturer: String? = null,
    val mpn: String? = null,
    val quantity: Int = 0,
    @SerialName("min_quantity") val minQuantity: Int = 0,
    val location: String? = null,
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
) {
    /** True when a min-stock threshold is set and current stock is below it. */
    val isLowStock: Boolean
        get() = minQuantity > 0 && quantity < minQuantity
}

/** A pedal build project. */
@Serializable
data class Project(
    val id: Int = 0,
    val name: String = "",
    val slug: String = "",
    @SerialName("effect_type") val effectType: String? = null,
    val status: String = "design", // design | prototype | production
    val description: String? = null,
    val notes: String? = null,
    @SerialName("schematic_id") val schematicId: Int? = null,
    @SerialName("created_at") val createdAt: String = "",
    @SerialName("updated_at") val updatedAt: String = "",
)

/** A single row of a project's bill of materials. */
@Serializable
data class BOMItem(
    val id: Int = 0,
    @SerialName("project_id") val projectId: Int = 0,
    @SerialName("component_id") val componentId: Int? = null,
    val reference: String? = null,
    val category: String = "",
    val value: String = "",
    val quantity: Int = 1,
    val notes: String? = null,
    @SerialName("is_optional") val isOptional: Int = 0, // 0/1
    @SerialName("created_at") val createdAt: String = "",
)

/** A parts supplier (reference / manual — only Mouser is a live searcher). */
@Serializable
data class Supplier(
    val id: Int = 0,
    val name: String = "",
    val slug: String = "",
    val website: String? = null,
    @SerialName("api_type") val apiType: String = "manual",
    @SerialName("poll_enabled") val pollEnabled: Int = 0,
    @SerialName("poll_interval") val pollInterval: Int = 86400,
    @SerialName("last_polled_at") val lastPolledAt: String? = null,
    @SerialName("created_at") val createdAt: String = "",
)

/** A cached supplier price listing. */
@Serializable
data class SupplierListing(
    val id: Int = 0,
    @SerialName("supplier_id") val supplierId: Int = 0,
    @SerialName("component_id") val componentId: Int? = null,
    val sku: String = "",
    val title: String = "",
    val price: Double = 0.0,
    val currency: String = "USD",
    @SerialName("in_stock") val inStock: Boolean = false,
    val url: String? = null,
    @SerialName("last_checked") val lastChecked: String = "",
)

/** An indexed schematic file (image or PDF) from the user-picked folder. */
@Serializable
data class Schematic(
    val id: Int = 0,
    @SerialName("category_folder") val categoryFolder: String = "",
    @SerialName("file_name") val fileName: String = "",
    @SerialName("file_path") val filePath: String = "",
    @SerialName("file_type") val fileType: String = "",
    @SerialName("file_size") val fileSize: Int? = null,
    @SerialName("effect_type") val effectType: String? = null,
    val tags: List<String>? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

/**
 * Transient supplier search result (never persisted directly). Matches the
 * SearchResult shape in the spec.
 */
data class SearchResult(
    val supplierSlug: String,
    val supplierName: String,
    val sku: String,
    val title: String,
    val price: Double,
    val currency: String,
    val inStock: Boolean,
    val url: String? = null,
)

// ─────────────────────────────────────────────────────────────────────────────
// Seed shapes: the bundled seed JSON uses a slightly leaner shape than the
// persisted models, so decode them into these and map into the real models on
// first run. Keeps the seed files identical to the Flet + macOS ports.
// ─────────────────────────────────────────────────────────────────────────────

/** Shape of one entry in assets/components.json. */
@Serializable
data class SeedComponent(
    val category: String,
    val subcategory: String? = null,
    val value: String,
    @SerialName("value_numeric") val valueNumeric: Double? = null,
    @SerialName("value_unit") val valueUnit: String? = null,
    val `package`: String? = null,
    val description: String? = null,
)

/** Shape of one entry in assets/suppliers.json. */
@Serializable
data class SeedSupplier(
    val name: String,
    val slug: String,
    val website: String? = null,
    @SerialName("api_type") val apiType: String = "manual",
    @SerialName("poll_interval") val pollInterval: Int = 86400,
)

/** Shape of one BOM row in assets/sample_project.json. */
@Serializable
data class SeedBOMItem(
    val reference: String? = null,
    val category: String,
    val value: String,
    val quantity: Int = 1,
    val notes: String? = null,
    @SerialName("is_optional") val isOptional: Int = 0,
)

/** Shape of assets/sample_project.json. */
@Serializable
data class SeedProject(
    val name: String,
    val slug: String,
    @SerialName("effect_type") val effectType: String? = null,
    val status: String = "design",
    val description: String? = null,
    val bom: List<SeedBOMItem> = emptyList(),
)
