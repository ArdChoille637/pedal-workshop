import Foundation
import Observation

/// Central observable store — loads all data from file-backed JSON resources.
/// No backend server required.
@Observable
@MainActor
public final class WorkshopStore {
    public static let shared = WorkshopStore()
    private let store = LocalDataStore.shared

    // MARK: – State
    public var summary: DashboardSummary?
    public var buildTiers: BuildTiers?
    public var components: [Component] = []
    public var projects: [Project] = []
    public var suppliers: [Supplier] = []
    public var schematics: [Schematic] = []

    public var supplierListings: [SupplierListing] = []

    public var isLoading = false
    public var error: String?

    // Search / filter state
    public var componentSearch = ""
    public var componentCategory = ""
    public var schematicSearch = ""

    // MARK: – Computed

    public var filteredComponents: [Component] {
        components.filter { c in
            (componentCategory.isEmpty || c.category == componentCategory) &&
            (componentSearch.isEmpty ||
             c.value.localizedCaseInsensitiveContains(componentSearch) ||
             (c.description?.localizedCaseInsensitiveContains(componentSearch) ?? false) ||
             c.category.localizedCaseInsensitiveContains(componentSearch))
        }
    }

    public var lowStockComponents: [Component] {
        components.filter(\.isLowStock)
    }

    public var componentCategories: [String] {
        Array(Set(components.map(\.category))).sorted()
    }

    // MARK: – Load all

    public func loadAll() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let comps  = try await store.fetchComponents()
            let projs  = try await store.fetchProjects()
            let sups   = try await store.fetchSuppliers()
            let schems = try await store.fetchSchematics(limit: 900)
            let allBOM = try await store.fetchAllBOMItems()

            components       = comps
            projects         = projs
            suppliers        = sups
            schematics       = schems
            supplierListings = (try? await store.fetchSupplierListings()) ?? []

            let tiers = BuildAnalyzer.analyze(
                projects: projs,
                bomItems: allBOM,
                components: comps
            )
            buildTiers = tiers
            summary    = BuildAnalyzer.summary(
                components: comps,
                projects: projs,
                tiers: tiers
            )

        } catch {
            self.error = error.localizedDescription
        }
    }

    // MARK: – Quantity adjustment

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
    public func createProjectFromSchematic(_ schematic: Schematic) async {
        do {
            guard let meta = try await store.fetchSchematicMeta(for: schematic.id),
                  meta.bomCount > 0 else {
                self.error = "No BOM data extracted for this schematic."
                return
            }
            let (project, _) = try await store.createProjectFromSchematic(schematic, meta: meta)
            // Reload projects list
            projects = try await store.fetchProjects()
            await recomputeTiers()
            self.error = nil
            self.lastCreatedProjectName = project.name
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Transient confirmation message after a project is auto-created.
    public var lastCreatedProjectName: String? = nil

    // MARK: – Convenience refreshes

    public func loadComponents() async { await loadAll() }
    public func loadProjects()   async { await loadAll() }
    public func loadSuppliers()  async { await loadAll() }

    // MARK: – Supplier price lookup

    /// Mouser API key (stored in UserDefaults)
    public var mouserAPIKey: String {
        get { UserDefaults.standard.string(forKey: "mouser_api_key") ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: "mouser_api_key") }
    }

    /// Search all Shopify suppliers (+ Mouser if key configured) for a query string.
    public func searchSuppliers(query: String) async -> [SupplierSearchResult] {
        await SupplierSearchService.shared.searchAll(query: query, mouserKey: mouserAPIKey)
    }

    /// Persist a price result, linked to a component.
    public func saveSupplierListing(_ result: SupplierSearchResult, for component: Component) async {
        let supplierId = supplierIdForSlug(result.supplierSlug)
        do {
            let listing = try await store.saveSupplierListing(
                result: result, supplierId: supplierId, componentId: component.id)
            // Update in-memory listings list
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

    public func listingsFor(_ component: Component) -> [SupplierListing] {
        supplierListings.filter { $0.componentId == component.id }
    }

    public func cheapestListing(for component: Component) -> SupplierListing? {
        listingsFor(component).filter { $0.inStock }.min(by: { $0.price < $1.price })
    }

    private func supplierIdForSlug(_ slug: String) -> Int {
        suppliers.first(where: { $0.slug == slug })?.id ?? 0
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

    // MARK: – Private

    func recomputeTiers() async {
        do {
            let allBOM = try await store.fetchAllBOMItems()
            let tiers = BuildAnalyzer.analyze(
                projects: projects,
                bomItems: allBOM,
                components: components
            )
            buildTiers = tiers
            summary    = BuildAnalyzer.summary(
                components: components,
                projects: projects,
                tiers: tiers
            )
            error = nil   // clear any prior error on successful recompute
        } catch {
            self.error = error.localizedDescription
        }
    }
}
