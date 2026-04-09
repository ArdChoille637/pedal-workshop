// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation
import Observation

// MARK: – WorkshopStore
//
// PURPOSE:
//   The single @Observable store that drives every SwiftUI view in the app.
//   Views read from it via `@Environment(WorkshopStore.self)` and call its
//   async methods to mutate data.
//
// ARCHITECTURE:
//   • @MainActor — all published state is mutated on the main thread so SwiftUI
//     receives updates correctly.  Expensive work is dispatched through the actor
//     isolation of LocalDataStore (a separate `actor`).
//   • @Observable (Swift 5.9+) — replaces ObservableObject/Published boilerplate.
//     Each stored property is automatically tracked; only accessed properties
//     trigger view re-renders.
//   • Singleton (shared) — one store for the whole app.  Tests can create their
//     own instance if needed, but the UI always uses WorkshopStore.shared.
//
// TO ADD NEW STATE:
//   1. Add a `public var myThings: [MyThing] = []` property.
//   2. Add a load call in `loadAll()`.
//   3. Add CRUD methods that call through to LocalDataStore and update the array.
//   4. Call `recomputeTiers()` after any mutation that affects build readiness.

@Observable
@MainActor
public final class WorkshopStore {

    // MARK: – Singleton

    public static let shared = WorkshopStore()

    // Private reference to the file-backed data layer.
    // All calls to `store` hop to the LocalDataStore actor's serial executor,
    // so mutations are always thread-safe even though we `await` them on MainActor.
    private let store = LocalDataStore.shared

    // MARK: – Published state

    /// Dashboard aggregates computed by BuildAnalyzer.
    public var summary:    DashboardSummary?
    /// Projects sorted into Ready / ARNA tiers.
    public var buildTiers: BuildTiers?

    public var components:       [Component]       = []
    public var projects:         [Project]         = []
    public var suppliers:        [Supplier]        = []
    public var schematics:       [Schematic]       = []
    public var supplierListings: [SupplierListing] = []

    /// Set to true while any async load is in progress.  Use for progress indicators.
    public var isLoading = false
    /// Localised error message from the most recent failed operation, or nil.
    /// Views should surface this in an alert or status bar.
    public var error: String?

    // MARK: – Search / filter state
    //
    // These are bound directly to searchable/picker controls via @Bindable.
    // Filtering is computed (see filteredComponents) rather than re-fetched from
    // disk, so it's instant.

    public var componentSearch   = ""   // free-text search across value, desc, MPN
    public var componentCategory = ""   // exact category filter ("resistor", etc.)
    public var schematicSearch   = ""   // free-text search for schematics

    // MARK: – Computed properties

    /// Components filtered by the current search and category state.
    /// O(n) on every access — cheap enough for typical inventory sizes (< 5 000 items).
    /// For larger catalogs, cache this in a @State or debounce the search input.
    public var filteredComponents: [Component] {
        components.filter { c in
            (componentCategory.isEmpty || c.category == componentCategory) &&
            (componentSearch.isEmpty   ||
             c.value.localizedCaseInsensitiveContains(componentSearch) ||
             (c.description?.localizedCaseInsensitiveContains(componentSearch) ?? false) ||
             c.category.localizedCaseInsensitiveContains(componentSearch) ||
             (c.mpn?.localizedCaseInsensitiveContains(componentSearch) ?? false))
        }
    }

    /// Components whose on-hand quantity is below their minimum threshold.
    public var lowStockComponents: [Component] { components.filter(\.isLowStock) }

    /// Sorted unique list of category strings for the picker UI.
    public var componentCategories: [String] {
        Array(Set(components.map(\.category))).sorted()
    }

    // MARK: – Initialisation

    private init() {
        // Migrate any API key that was previously stored in UserDefaults.
        // This is a one-time migration; after it runs the key lives in the Keychain.
        KeychainHelper.migrateFromDefaults(key: "mouser_api_key")
    }

    // MARK: – Load all data

    /// Loads every collection from disk and recomputes build tiers.
    /// Call this on app launch and whenever you want a full refresh.
    ///
    /// Loading is sequential through the LocalDataStore actor to avoid
    /// concurrent file reads on the same cache.  Total time is typically
    /// < 100 ms for a full inventory.
    public func loadAll() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let comps  = try await store.fetchComponents()
            let projs  = try await store.fetchProjects()
            let sups   = try await store.fetchSuppliers()
            let schems = try await store.fetchSchematics(limit: 900)
            let allBOM = try await store.fetchAllBOMItems()
            let listings = (try? await store.fetchSupplierListings()) ?? []

            components       = comps
            projects         = projs
            suppliers        = sups
            schematics       = schems
            supplierListings = listings

            // BuildAnalyzer is pure computation — no I/O — so calling it on
            // MainActor is fine; it finishes in microseconds.
            let tiers = BuildAnalyzer.analyze(
                projects:   projs,
                bomItems:   allBOM,
                components: comps
            )
            buildTiers = tiers
            summary    = BuildAnalyzer.summary(components: comps, projects: projs, tiers: tiers)

        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – Quantity adjustment

    /// Increment or decrement a component's on-hand quantity.
    /// `delta` is positive to add stock, negative to consume it.
    /// Quantity floors at 0 (see LocalDataStore.adjustQuantity).
    public func adjustQuantity(component: Component, delta: Int) async {
        do {
            let updated = try await store.adjustQuantity(id: component.id, delta: delta)
            if let idx = components.firstIndex(where: { $0.id == component.id }) {
                components[idx] = updated
            }
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – Component CRUD

    public func addComponent(_ form: ComponentForm) async {
        do {
            let new = try await store.addComponent(form)
            components.append(new)
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func updateComponent(_ component: Component) async {
        do {
            let updated = try await store.updateComponent(component)
            if let idx = components.firstIndex(where: { $0.id == updated.id }) {
                components[idx] = updated
            }
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func deleteComponent(_ component: Component) async {
        do {
            try await store.deleteComponent(id: component.id)
            components.removeAll { $0.id == component.id }
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – Project CRUD

    public func addProject(_ form: ProjectForm) async {
        do {
            let new = try await store.addProject(form)
            projects.append(new)
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func updateProject(_ project: Project) async {
        do {
            let updated = try await store.updateProject(project)
            if let idx = projects.firstIndex(where: { $0.id == updated.id }) {
                projects[idx] = updated
            }
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func deleteProject(_ project: Project) async {
        do {
            try await store.deleteProject(id: project.id)
            projects.removeAll { $0.id == project.id }
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – BOM CRUD

    public func addBOMItem(_ form: BOMItemForm, to project: Project) async {
        do {
            _ = try await store.addBOMItem(form, projectId: project.id)
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func deleteBOMItem(_ item: BOMItem) async {
        do {
            try await store.deleteBOMItem(id: item.id)
            await recomputeTiers()
        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – Schematic metadata

    public func schematicMeta(for schematic: Schematic) async -> SchematicMeta? {
        try? await store.fetchSchematicMeta(for: schematic.id)
    }

    /// Create a project + full BOM from an OCR-analyzed schematic.
    /// Sets `lastCreatedProjectName` on success so the UI can show a confirmation.
    public func createProjectFromSchematic(_ schematic: Schematic) async {
        do {
            guard let meta = try await store.fetchSchematicMeta(for: schematic.id),
                  meta.bomCount > 0 else {
                self.error = "No BOM data for this schematic. Run analyze_schematics.py first."
                return
            }
            let (project, _) = try await store.createProjectFromSchematic(schematic, meta: meta)
            projects = try await store.fetchProjects()
            await recomputeTiers()
            self.error = nil
            self.lastCreatedProjectName = project.name
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Transient: set to the just-created project name after createProjectFromSchematic.
    /// Views should observe this and clear it after showing confirmation.
    public var lastCreatedProjectName: String? = nil

    // MARK: – Convenience refreshes
    //
    // These all call loadAll() — cheap since LocalDataStore caches in memory.
    // If collections become large, consider loading only the changed collection.

    public func loadComponents() async { await loadAll() }
    public func loadProjects()   async { await loadAll() }
    public func loadSuppliers()  async { await loadAll() }

    // MARK: – Supplier price lookup

    /// The Mouser API key is stored in the Keychain (not UserDefaults) for security.
    ///
    /// Get a free key at https://www.mouser.com/api-hub/
    /// The key is read/written through KeychainHelper — it never touches UserDefaults.
    public var mouserAPIKey: String {
        get { KeychainHelper.get("mouser_api_key") ?? "" }
        set {
            if newValue.isEmpty {
                KeychainHelper.delete("mouser_api_key")
            } else {
                KeychainHelper.set(newValue, forKey: "mouser_api_key")
            }
        }
    }

    /// Search all configured suppliers in parallel.
    /// Tayda / Mammoth / Love My Switches require no key.
    /// Mouser is included only if `mouserAPIKey` is non-empty.
    public func searchSuppliers(query: String) async -> [SupplierSearchResult] {
        await SupplierSearchService.shared.searchAll(query: query, mouserKey: mouserAPIKey)
    }

    /// Persist a supplier search result linked to a component.
    /// If a listing for the same supplier + SKU already exists it is updated.
    public func saveSupplierListing(_ result: SupplierSearchResult, for component: Component) async {
        let supplierId = supplierIdForSlug(result.supplierSlug)
        do {
            let listing = try await store.saveSupplierListing(
                result: result, supplierId: supplierId, componentId: component.id
            )
            if let idx = supplierListings.firstIndex(where: { $0.id == listing.id }) {
                supplierListings[idx] = listing
            } else {
                supplierListings.append(listing)
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func deleteSupplierListing(_ listing: SupplierListing) async {
        do {
            try await store.deleteSupplierListing(id: listing.id)
            supplierListings.removeAll { $0.id == listing.id }
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// All saved listings for a specific component.
    public func listingsFor(_ component: Component) -> [SupplierListing] {
        supplierListings.filter { $0.componentId == component.id }
    }

    /// The cheapest in-stock listing for a component, or nil if none saved.
    public func cheapestListing(for component: Component) -> SupplierListing? {
        listingsFor(component).filter { $0.inStock }.min(by: { $0.price < $1.price })
    }

    // MARK: – Schematic search

    public func searchSchematics(_ q: String) async {
        do {
            schematics = try await store.fetchSchematics(q: q.isEmpty ? nil : q, limit: 900)
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func schematicFileURL(for schematic: Schematic) -> URL? {
        URL(fileURLWithPath: schematic.filePath)
    }

    // MARK: – Private helpers

    /// Re-run the build analyzer after any mutation that affects part availability.
    /// This is fast (pure in-memory computation) so calling it on every write is fine.
    func recomputeTiers() async {
        do {
            let allBOM = try await store.fetchAllBOMItems()
            let tiers  = BuildAnalyzer.analyze(
                projects:   projects,
                bomItems:   allBOM,
                components: components
            )
            buildTiers = tiers
            summary    = BuildAnalyzer.summary(
                components: components, projects: projects, tiers: tiers
            )
            error = nil   // clear stale error on successful recompute
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func supplierIdForSlug(_ slug: String) -> Int {
        suppliers.first(where: { $0.slug == slug })?.id ?? 0
    }
}
