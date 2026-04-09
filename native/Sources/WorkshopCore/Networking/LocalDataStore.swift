// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

// MARK: – LocalDataStore
//
// PURPOSE:
//   Single source of truth for all app data.  Uses plain JSON files stored in
//   ~/Library/Application Support/PedalWorkshop/ so data survives app updates,
//   works without a server, and is easy to inspect / hand-edit.
//
// ARCHITECTURE:
//   • `actor` isolation — all mutations are serialised on the actor's executor,
//     so there are no data races even when called from concurrent async contexts.
//   • In-memory cache — each collection is loaded once and mutated in place;
//     writes flush the full array back to disk atomically (.atomic flag).
//   • Bundle seeding — on first launch, seed files from the app bundle are
//     copied to Application Support so the user starts with useful defaults.
//
// TO ADD A NEW DATA TYPE:
//   1. Define the model struct in Sources/WorkshopCore/Models/.
//   2. Add a `private var _myThings: [MyThing]?` cache property here.
//   3. Add a private `myThings()` accessor that lazy-loads from disk.
//   4. Add public fetch / add / update / delete methods following the pattern below.
//   5. Add a seed JSON file to Sources/WorkshopCore/Resources/ if needed.
//   6. Register the resource in Package.swift → resources: [.process(...)].

public actor LocalDataStore: Sendable {

    // Shared singleton — use this everywhere.
    // If you need test isolation, create a separate instance instead.
    public static let shared = LocalDataStore()

    // MARK: – Codec

    // We use explicit CodingKeys with snake_case raw values on every model,
    // so no key-decoding strategy is needed here.  This avoids surprises when
    // property names contain acronyms (e.g. `mpn`, `bomItems`).
    private let decoder = JSONDecoder()

    // Pretty-printed so the JSON files are human-readable and diff-friendly
    // in version control.  To shrink file size in production builds, remove
    // .prettyPrinted — the decoder doesn't care either way.
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.outputFormatting = [.prettyPrinted, .sortedKeys]
        return e
    }()

    // MARK: – ISO 8601 timestamp helper
    //
    // WHY cached: ISO8601DateFormatter is expensive to initialise (~5 ms).
    // Creating one per write would be noticeable during bulk BOM imports.
    private let iso8601: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private func now() -> String { iso8601.string(from: Date()) }

    // MARK: – In-memory cache
    //
    // Optional means "not loaded yet".  Once loaded the value is never nil;
    // mutations keep it in sync so we never need a full reload from disk.
    private var _components:       [Component]?
    private var _suppliers:        [Supplier]?
    private var _projects:         [Project]?
    private var _bomItems:         [BOMItem]?
    private var _schematics:       [Schematic]?
    private var _schematicMeta:    [Int: SchematicMeta]?   // keyed by schematic.id
    private var _supplierListings: [SupplierListing]?

    // MARK: – Application Support directory

    // The directory is created here once; subsequent accesses are pure URL math.
    // Force-unwrap of `urls(for:in:)` is safe — this call cannot fail on macOS/iOS.
    private let appSupportDir: URL = {
        let base = FileManager.default.urls(
            for: .applicationSupportDirectory, in: .userDomainMask
        ).first!
        let dir = base.appendingPathComponent("PedalWorkshop", isDirectory: true)
        // createDirectory is idempotent when withIntermediateDirectories: true
        do {
            try FileManager.default.createDirectory(
                at: dir, withIntermediateDirectories: true, attributes: nil
            )
        } catch {
            // In practice this cannot fail for a user-writable directory.
            // If it does (e.g. permission error), reads will subsequently fail
            // with a clear DataError.missingResource message.
            assertionFailure("Could not create app support directory: \(error)")
        }
        return dir
    }()

    private init() {}

    // MARK: – Path helpers

    /// Returns the on-disk URL for a named JSON file (no extension needed).
    private func dataURL(_ name: String) -> URL {
        appSupportDir.appendingPathComponent("\(name).json")
    }

    // MARK: – Generic load / save

    /// Load a JSON file from Application Support.
    /// On first launch (file absent), copies the seed from the app bundle.
    ///
    /// - Parameters:
    ///   - name: File base-name (e.g. "components" → components.json).
    ///   - bundleName: Override if the bundle resource has a different name.
    private func load<T: Decodable>(_ name: String, type: T.Type, bundleName: String? = nil) throws -> T {
        let dest = dataURL(name)

        if !FileManager.default.fileExists(atPath: dest.path) {
            // First launch — seed from bundle.
            // To change the defaults a user sees on first launch, edit the
            // JSON files in Sources/WorkshopCore/Resources/.
            let bname = bundleName ?? name
            guard let src = Bundle.module.url(forResource: bname, withExtension: "json") else {
                throw DataError.missingResource(bname)
            }
            try FileManager.default.copyItem(at: src, to: dest)
        }

        let data = try Data(contentsOf: dest)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            // Surface decode errors with context so contributors can diagnose
            // schema mismatches after model changes.
            throw DataError.decodeFailed(name, underlying: error)
        }
    }

    /// Atomically write an encodable value to disk.
    /// `.atomic` writes to a temp file then renames, preventing corruption on
    /// crash or sudden power loss.
    private func save<T: Encodable>(_ value: T, name: String) throws {
        let data = try encoder.encode(value)
        try data.write(to: dataURL(name), options: .atomic)
    }

    // MARK: – Next ID helper
    //
    // Generates monotonically-increasing integer IDs — simple and deterministic
    // for a local JSON store.  If you ever migrate to a networked backend,
    // switch to UUID strings and update the Identifiable conformances.
    private func nextId(_ items: [some Identifiable<Int>]) -> Int {
        (items.map(\.id).max() ?? 0) + 1
    }

    // MARK: – Slug helper
    //
    // Produces a URL-safe lowercase hyphenated slug from any name.
    // Used for project slugs; kept simple — collisions are benign.
    private func makeSlug(_ name: String) -> String {
        name.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
            .joined(separator: "-")
    }

    // =========================================================================
    // MARK: – Cache accessors (private)
    // =========================================================================

    private func components() throws -> [Component] {
        if _components == nil {
            _components = try load("components", type: [Component].self)
        }
        return _components!
    }

    private func projects() throws -> [Project] {
        if _projects == nil { try seedProjectsIfNeeded() }
        return _projects!
    }

    private func bomItems() throws -> [BOMItem] {
        if _bomItems == nil { try seedProjectsIfNeeded() }
        return _bomItems!
    }

    /// On first launch the bundle ships a combined `projects.json` containing
    /// `{ "projects": [...], "bom_items": [...] }`.  We split them into
    /// separate writable files so they can grow independently.
    ///
    /// TO CHANGE DEFAULT PROJECTS: edit seeds/sample_project.json and
    /// re-run `make seed` (Python) or rebuild the Swift target.
    private func seedProjectsIfNeeded() throws {
        let projDest = dataURL("projects")
        let bomDest  = dataURL("bom_items")

        if FileManager.default.fileExists(atPath: projDest.path),
           FileManager.default.fileExists(atPath: bomDest.path) {
            _projects = try load("projects",  type: [Project].self)
            _bomItems = try load("bom_items", type: [BOMItem].self)
            return
        }

        // Bundle ships projects + BOM items in one file to keep the seed tidy.
        guard let src = Bundle.module.url(forResource: "projects", withExtension: "json") else {
            // No seed file — start empty rather than crashing.
            _projects = []
            _bomItems = []
            try save(_projects!, name: "projects")
            try save(_bomItems!, name: "bom_items")
            return
        }

        let data   = try Data(contentsOf: src)
        let bundle = try decoder.decode(ProjectBundle.self, from: data)
        try save(bundle.projects, name: "projects")
        try save(bundle.bomItems, name: "bom_items")
        _projects = bundle.projects
        _bomItems = bundle.bomItems
    }

    // =========================================================================
    // MARK: – Components
    // =========================================================================

    /// Fetch all components, optionally filtered by category and/or search query.
    /// Both filters are applied server-side (in-memory) — no SQL needed.
    public func fetchComponents(category: String? = nil, q: String? = nil) throws -> [Component] {
        var result = try components()
        if let cat = category, !cat.isEmpty {
            result = result.filter { $0.category == cat }
        }
        if let query = q, !query.isEmpty {
            let lower = query.lowercased()
            result = result.filter {
                $0.value.lowercased().contains(lower) ||
                ($0.description?.lowercased().contains(lower) ?? false) ||
                $0.category.lowercased().contains(lower) ||
                ($0.mpn?.lowercased().contains(lower) ?? false)
            }
        }
        return result
    }

    /// Add a new component from a form.  Returns the persisted component with
    /// its generated `id` filled in.
    public func addComponent(_ form: ComponentForm) throws -> Component {
        var all = try components()
        let ts  = now()
        let new = Component(
            id:           nextId(all),
            category:     form.category,
            subcategory:  form.subcategory.nilIfEmpty,
            value:        form.value,
            valueNumeric: nil,      // TODO: parse numeric from value string (e.g. "10k" → 10000)
            valueUnit:    form.valueUnit.nilIfEmpty,
            package:      form.package.nilIfEmpty,
            description:  form.description.nilIfEmpty,
            manufacturer: form.manufacturer.nilIfEmpty,
            mpn:          form.mpn.nilIfEmpty,
            quantity:     form.quantity,
            minQuantity:  form.minQuantity,
            location:     form.location.nilIfEmpty,
            notes:        form.notes.nilIfEmpty,
            createdAt:    ts,
            updatedAt:    ts
        )
        all.append(new)
        _components = all
        try save(all, name: "components")
        return new
    }

    public func updateComponent(_ updated: Component) throws -> Component {
        var all = try components()
        guard let idx = all.firstIndex(where: { $0.id == updated.id }) else {
            throw DataError.notFound(updated.id)
        }
        var mut = updated
        mut.updatedAt = now()
        all[idx]  = mut
        _components = all
        try save(all, name: "components")
        return mut
    }

    public func deleteComponent(id: Int) throws {
        var all = try components()
        guard let idx = all.firstIndex(where: { $0.id == id }) else {
            throw DataError.notFound(id)
        }
        all.remove(at: idx)
        _components = all
        try save(all, name: "components")

        // Preserve BOM integrity: nil out the component link on any BOM rows
        // that referenced this component.  The BOM row itself is kept so the
        // project still knows a part is needed — it just loses the inventory link.
        var boms = try bomItems()
        var bomChanged = false
        for i in boms.indices where boms[i].componentId == id {
            boms[i].componentId = nil
            bomChanged = true
        }
        if bomChanged {
            _bomItems = boms
            try save(boms, name: "bom_items")
        }
    }

    /// Adjust inventory quantity by `delta` (positive = add stock, negative = consume).
    /// Clamps to 0 — quantity can never go negative.
    public func adjustQuantity(id: Int, delta: Int) throws -> Component {
        var all = try components()
        guard let idx = all.firstIndex(where: { $0.id == id }) else {
            throw DataError.notFound(id)
        }
        // max(0, ...) prevents negative stock, which has no physical meaning
        all[idx].quantity  = max(0, all[idx].quantity + delta)
        all[idx].updatedAt = now()
        let updated = all[idx]
        _components = all
        try save(all, name: "components")
        return updated
    }

    // =========================================================================
    // MARK: – Projects
    // =========================================================================

    public func fetchProjects() throws -> [Project] { try projects() }

    public func addProject(_ form: ProjectForm) throws -> Project {
        var all = try projects()
        let ts   = now()
        let new  = Project(
            id:          nextId(all),
            name:        form.name,
            slug:        makeSlug(form.name),
            effectType:  form.effectType.nilIfEmpty,
            status:      form.status,
            description: form.description.nilIfEmpty,
            notes:       form.notes.nilIfEmpty,
            schematicId: nil,
            createdAt:   ts,
            updatedAt:   ts
        )
        all.append(new)
        _projects = all
        try save(all, name: "projects")
        return new
    }

    public func updateProject(_ updated: Project) throws -> Project {
        var all = try projects()
        guard let idx = all.firstIndex(where: { $0.id == updated.id }) else {
            throw DataError.notFound(updated.id)
        }
        var mut = updated
        mut.updatedAt = now()
        all[idx]  = mut
        _projects = all
        try save(all, name: "projects")
        return mut
    }

    public func deleteProject(id: Int) throws {
        var all = try projects()
        guard let idx = all.firstIndex(where: { $0.id == id }) else {
            throw DataError.notFound(id)
        }
        all.remove(at: idx)
        _projects = all
        try save(all, name: "projects")

        // Cascade delete: remove all BOM rows belonging to this project.
        // This mirrors the ON DELETE CASCADE behaviour you'd get in SQLite.
        var boms = try bomItems()
        boms.removeAll { $0.projectId == id }
        _bomItems = boms
        try save(boms, name: "bom_items")
    }

    // =========================================================================
    // MARK: – BOM Items
    // =========================================================================

    public func fetchBOMItems(projectId: Int) throws -> [BOMItem] {
        try bomItems().filter { $0.projectId == projectId }
    }

    public func fetchAllBOMItems() throws -> [BOMItem] { try bomItems() }

    public func addBOMItem(_ form: BOMItemForm, projectId: Int) throws -> BOMItem {
        var all = try bomItems()
        let new = BOMItem(
            id:          nextId(all),
            projectId:   projectId,
            componentId: form.componentId,
            reference:   form.reference.nilIfEmpty,
            category:    form.category,
            value:       form.value,
            quantity:    form.quantity,
            notes:       form.notes.nilIfEmpty,
            // Stored as Int (0/1) for compatibility with the Python/SQLite backend.
            // To change to a Bool column, update BOMItem.isOptional type and CodingKeys.
            isOptional:  form.isOptional ? 1 : 0,
            createdAt:   now()
        )
        all.append(new)
        _bomItems = all
        try save(all, name: "bom_items")
        return new
    }

    public func updateBOMItem(_ updated: BOMItem) throws -> BOMItem {
        var all = try bomItems()
        guard let idx = all.firstIndex(where: { $0.id == updated.id }) else {
            throw DataError.notFound(updated.id)
        }
        all[idx]  = updated
        _bomItems = all
        try save(all, name: "bom_items")
        return updated
    }

    public func deleteBOMItem(id: Int) throws {
        var all = try bomItems()
        guard let idx = all.firstIndex(where: { $0.id == id }) else {
            throw DataError.notFound(id)
        }
        all.remove(at: idx)
        _bomItems = all
        try save(all, name: "bom_items")
    }

    // =========================================================================
    // MARK: – Suppliers (read-only — edit suppliers.json in bundle to change)
    // =========================================================================

    /// Suppliers are defined in the bundle's suppliers.json seed file.
    /// To add a new supplier:
    ///   1. Add an entry to Sources/WorkshopCore/Resources/suppliers.json.
    ///   2. Implement a Swift adapter in SupplierSearch.swift (Shopify stores
    ///      need only a new ShopifySearcher instance; others need a custom actor).
    ///   3. Register the adapter in SupplierSearchService.searchAll().
    public func fetchSuppliers() throws -> [Supplier] {
        if _suppliers == nil {
            _suppliers = try load("suppliers", type: [Supplier].self)
        }
        return _suppliers!
    }

    // =========================================================================
    // MARK: – Schematics (read-only index)
    // =========================================================================

    /// The schematics index is generated by scripts/index_schematics.py and
    /// written to Application Support.  It is never edited by the app itself.
    ///
    /// - Parameters:
    ///   - q: Free-text search across filename, folder, and effect type.
    ///   - category: Exact folder match (e.g. "Fuzz and Fuzzy Noisemakers").
    ///   - limit: Max results — keep reasonable to avoid huge List renders.
    public func fetchSchematics(q: String? = nil, category: String? = nil, limit: Int = 500) throws -> [Schematic] {
        if _schematics == nil {
            _schematics = try load("schematics", type: [Schematic].self)
        }
        var result = _schematics!
        if let cat = category, !cat.isEmpty {
            result = result.filter { $0.categoryFolder == cat }
        }
        if let query = q, !query.isEmpty {
            let lower = query.lowercased()
            result = result.filter {
                $0.fileName.lowercased().contains(lower) ||
                $0.categoryFolder.lowercased().contains(lower) ||
                ($0.effectType?.lowercased().contains(lower) ?? false)
            }
        }
        return Array(result.prefix(limit))
    }

    // =========================================================================
    // MARK: – Schematic Metadata (OCR-extracted BOM)
    // =========================================================================

    /// Returns the OCR-extracted BOM metadata for all schematics, keyed by id.
    /// Returns an empty dict (not an error) when the file doesn't exist yet —
    /// the user just hasn't run `analyze_schematics.py` yet.
    ///
    /// To regenerate: `python3 scripts/analyze_schematics.py --workers 6`
    /// The script writes to ~/Library/Application Support/PedalWorkshop/schematics_metadata.json
    public func fetchSchematicMeta() throws -> [Int: SchematicMeta] {
        if let cached = _schematicMeta { return cached }
        let url = appSupportDir.appendingPathComponent("schematics_metadata.json")
        guard FileManager.default.fileExists(atPath: url.path) else { return [:] }
        let data  = try Data(contentsOf: url)
        let items = try decoder.decode([SchematicMeta].self, from: data)
        // Build a dictionary for O(1) lookups by schematic ID
        let dict  = Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0) })
        _schematicMeta = dict
        return dict
    }

    public func fetchSchematicMeta(for id: Int) throws -> SchematicMeta? {
        try fetchSchematicMeta()[id]
    }

    /// Creates a new Project + full BOM from a schematic's OCR-extracted metadata.
    ///
    /// - Parameters:
    ///   - schematic: The schematic to derive the project from.
    ///   - meta: Pre-fetched OCR metadata (call fetchSchematicMeta(for:) first).
    ///   - status: Initial project status — defaults to "design".
    ///
    /// TO CUSTOMISE AUTO-NAMING: modify the `name` and `form` construction below.
    public func createProjectFromSchematic(
        _ schematic: Schematic,
        meta: SchematicMeta,
        status: String = "design"
    ) throws -> (Project, [BOMItem]) {
        // Strip file extension for a cleaner project name
        let name = (schematic.fileName as NSString).deletingPathExtension
        let form = ProjectForm(
            name:        name,
            effectType:  schematic.effectType
                         ?? schematic.categoryFolder
                            .components(separatedBy: " ").first?
                            .lowercased() ?? "",
            status:      status,
            description: "Created from schematic: \(schematic.categoryFolder)",
            notes:       "Source file: \(schematic.filePath)"
        )
        let project = try addProject(form)

        var created: [BOMItem] = []
        for entry in meta.bomEntries {
            var itemForm         = BOMItemForm()
            itemForm.category    = entry.category
            itemForm.value       = entry.value
            itemForm.quantity    = entry.quantity

            // Attempt to link to an existing inventory component.
            // Matching is case-insensitive on both category and value.
            // To improve match quality, consider normalising values (e.g. "10k" == "10K")
            // in Component.normalizedValue before comparing.
            if let comps = _components {
                itemForm.componentId = comps.first {
                    $0.category == entry.category &&
                    $0.value.lowercased() == entry.value.lowercased()
                }?.id
            }

            created.append(try addBOMItem(itemForm, projectId: project.id))
        }
        return (project, created)
    }

    // =========================================================================
    // MARK: – Supplier Listings
    // =========================================================================
    //
    // Supplier listings record prices saved from PriceLookupView.
    // They are NOT polled automatically — the user triggers searches manually.
    // For automatic polling, see api/tasks/scheduler.py (Python backend).

    private func supplierListings() throws -> [SupplierListing] {
        if _supplierListings == nil {
            let url = dataURL("supplier_listings")
            if FileManager.default.fileExists(atPath: url.path) {
                let data = try Data(contentsOf: url)
                _supplierListings = try decoder.decode([SupplierListing].self, from: data)
            } else {
                // No listings yet — start empty.  File is created on first save.
                _supplierListings = []
            }
        }
        return _supplierListings!
    }

    public func fetchSupplierListings(componentId: Int? = nil) throws -> [SupplierListing] {
        var all = try supplierListings()
        if let cid = componentId { all = all.filter { $0.componentId == cid } }
        return all
    }

    /// Save (or update) a supplier search result as a linked listing.
    /// If a listing for the same supplier + component + SKU already exists,
    /// its price and stock status are refreshed rather than creating a duplicate.
    public func saveSupplierListing(
        result: SupplierSearchResult,
        supplierId: Int,
        componentId: Int?
    ) throws -> SupplierListing {
        var all = try supplierListings()
        let ts  = now()

        if let idx = all.firstIndex(where: {
            $0.supplierId  == supplierId &&
            $0.componentId == componentId &&
            $0.sku         == result.sku
        }) {
            // Update existing — refresh price + stock, preserve other fields
            all[idx].price       = result.price
            all[idx].inStock     = result.inStock
            all[idx].lastChecked = ts
            _supplierListings    = all
            try save(all, name: "supplier_listings")
            return all[idx]
        }

        let new = SupplierListing(
            id:          nextId(all),
            supplierId:  supplierId,
            componentId: componentId,
            sku:         result.sku,
            title:       result.title,
            price:       result.price,
            currency:    result.currency,
            inStock:     result.inStock,
            url:         result.url?.absoluteString,
            lastChecked: ts
        )
        all.append(new)
        _supplierListings = all
        try save(all, name: "supplier_listings")
        return new
    }

    public func deleteSupplierListing(id: Int) throws {
        var all = try supplierListings()
        all.removeAll { $0.id == id }
        _supplierListings = all
        try save(all, name: "supplier_listings")
    }
}

// MARK: – Error types

public enum DataError: LocalizedError, Sendable {
    case missingResource(String)
    case notFound(Int)
    case decodeFailed(String, underlying: Error)

    public var errorDescription: String? {
        switch self {
        case .missingResource(let n):
            return "Bundled resource not found: \(n).json — rebuild the app to re-seed."
        case .notFound(let id):
            return "Record id=\(id) not found — it may have been deleted."
        case .decodeFailed(let name, let err):
            // This usually means the JSON schema changed without migrating existing data.
            // Fix: delete ~/Library/Application Support/PedalWorkshop/\(name).json
            // and relaunch to re-seed from bundle defaults.
            return "Failed to decode \(name).json: \(err.localizedDescription)"
        }
    }
}

// MARK: – Bundle seed helper

// projects.json in the bundle stores both arrays in one file for tidiness.
// After first launch they're split into separate writable files.
private struct ProjectBundle: Codable, Sendable {
    let projects: [Project]
    let bomItems: [BOMItem]

    enum CodingKeys: String, CodingKey {
        case projects
        case bomItems = "bom_items"
    }
}
