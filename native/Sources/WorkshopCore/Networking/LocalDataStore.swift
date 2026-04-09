import Foundation

// MARK: – File-backed data store
// On first launch copies bundled JSON to ~/Library/Application Support/PedalWorkshop/
// and uses those writable files for all subsequent reads and writes.

public actor LocalDataStore: Sendable {
    public static let shared = LocalDataStore()

    // MARK: – Codec

    private let decoder: JSONDecoder = JSONDecoder()
    // Models use explicit CodingKeys with snake_case raw values – no strategy needed.
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.outputFormatting = .prettyPrinted
        return e
    }()

    // MARK: – In-memory cache

    private var _components:       [Component]?
    private var _suppliers:        [Supplier]?
    private var _projects:         [Project]?
    private var _bomItems:         [BOMItem]?
    private var _schematics:       [Schematic]?
    private var _schematicMeta:    [Int: SchematicMeta]?   // keyed by schematic id
    private var _supplierListings: [SupplierListing]?

    // MARK: – Application Support directory

    private let appSupportDir: URL = {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir  = base.appendingPathComponent("PedalWorkshop", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }()

    private init() {}

    // MARK: – Path helpers

    private func dataURL(_ name: String) -> URL {
        appSupportDir.appendingPathComponent("\(name).json")
    }

    // MARK: – Generic load / save

    /// Load from Application Support; on first run copy from bundle.
    private func load<T: Decodable>(_ name: String, type: T.Type, bundleName: String? = nil) throws -> T {
        let dest = dataURL(name)
        if !FileManager.default.fileExists(atPath: dest.path) {
            // First launch: seed from bundle
            let bname = bundleName ?? name
            guard let src = Bundle.module.url(forResource: bname, withExtension: "json") else {
                throw DataError.missingResource(bname)
            }
            try FileManager.default.copyItem(at: src, to: dest)
        }
        let data = try Data(contentsOf: dest)
        return try decoder.decode(T.self, from: data)
    }

    private func save<T: Encodable>(_ value: T, name: String) throws {
        let data = try encoder.encode(value)
        try data.write(to: dataURL(name), options: .atomic)
    }

    // MARK: – Cache accessors

    private func components() throws -> [Component] {
        if _components == nil {
            _components = try load("components", type: [Component].self)
        }
        return _components!
    }

    private func projects() throws -> [Project] {
        if _projects == nil {
            try seedProjectsIfNeeded()
        }
        return _projects!
    }

    private func bomItems() throws -> [BOMItem] {
        if _bomItems == nil {
            try seedProjectsIfNeeded()
        }
        return _bomItems!
    }

    /// On first launch the bundle ships a combined projects.json with {projects, bom_items}.
    /// We split them into separate files in Application Support.
    private func seedProjectsIfNeeded() throws {
        let projDest = dataURL("projects")
        let bomDest  = dataURL("bom_items")

        if FileManager.default.fileExists(atPath: projDest.path) &&
           FileManager.default.fileExists(atPath: bomDest.path) {
            _projects = try load("projects",   type: [Project].self)
            _bomItems = try load("bom_items",  type: [BOMItem].self)
            return
        }

        // Seed from bundle combined format
        guard let src = Bundle.module.url(forResource: "projects", withExtension: "json") else {
            throw DataError.missingResource("projects")
        }
        let data   = try Data(contentsOf: src)
        let bundle = try decoder.decode(ProjectBundle.self, from: data)

        try save(bundle.projects,  name: "projects")
        try save(bundle.bomItems,  name: "bom_items")

        _projects = bundle.projects
        _bomItems  = bundle.bomItems
    }

    // MARK: – Next ID helpers

    private func nextId(_ items: [some Identifiable<Int>]) -> Int {
        (items.map(\.id).max() ?? 0) + 1
    }

    // MARK: – ISO 8601 timestamp

    private func now() -> String {
        ISO8601DateFormatter().string(from: Date())
    }

    // =========================================================================
    // MARK: – Components
    // =========================================================================

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
                $0.category.lowercased().contains(lower)
            }
        }
        return result
    }

    public func addComponent(_ form: ComponentForm) throws -> Component {
        var all = try components()
        let ts  = now()
        let new = Component(
            id:           nextId(all),
            category:     form.category,
            subcategory:  form.subcategory.nilIfEmpty,
            value:        form.value,
            valueNumeric: nil,
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
        all[idx] = mut
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

        // Nil out component_id on linked BOM items
        var boms = try bomItems()
        var changed = false
        for i in boms.indices where boms[i].componentId == id {
            boms[i].componentId = nil
            changed = true
        }
        if changed {
            _bomItems = boms
            try save(boms, name: "bom_items")
        }
    }

    public func adjustQuantity(id: Int, delta: Int) throws -> Component {
        var all = try components()
        guard let idx = all.firstIndex(where: { $0.id == id }) else {
            throw DataError.notFound(id)
        }
        all[idx].quantity = max(0, all[idx].quantity + delta)
        all[idx].updatedAt = now()
        let updated = all[idx]
        _components = all
        try save(all, name: "components")
        return updated
    }

    // =========================================================================
    // MARK: – Projects
    // =========================================================================

    public func fetchProjects() throws -> [Project] {
        try projects()
    }

    public func addProject(_ form: ProjectForm) throws -> Project {
        var all = try projects()
        let ts  = now()
        let slug = makeSlug(form.name)
        let new = Project(
            id:          nextId(all),
            name:        form.name,
            slug:        slug,
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
        all[idx] = mut
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

        // Delete all BOM items for this project
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

    public func fetchAllBOMItems() throws -> [BOMItem] {
        try bomItems()
    }

    public func addBOMItem(_ form: BOMItemForm, projectId: Int) throws -> BOMItem {
        var all = try bomItems()
        let ts  = now()
        let new = BOMItem(
            id:          nextId(all),
            projectId:   projectId,
            componentId: form.componentId,
            reference:   form.reference.nilIfEmpty,
            category:    form.category,
            value:       form.value,
            quantity:    form.quantity,
            notes:       form.notes.nilIfEmpty,
            isOptional:  form.isOptional ? 1 : 0,
            createdAt:   ts
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
        all[idx] = updated
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
    // MARK: – Suppliers & Schematics (read-only)
    // =========================================================================

    public func fetchSuppliers() throws -> [Supplier] {
        if _suppliers == nil {
            _suppliers = try load("suppliers", type: [Supplier].self)
        }
        return _suppliers!
    }

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

    public func schematicFileURL(path: String) -> URL? {
        URL(fileURLWithPath: path)
    }

    // =========================================================================
    // MARK: – Schematic Metadata (OCR-extracted BOM)
    // =========================================================================

    /// Load OCR metadata for all schematics. Returns nil if the metadata file
    /// hasn't been generated yet (run analyze_schematics.py first).
    public func fetchSchematicMeta() throws -> [Int: SchematicMeta] {
        if let cached = _schematicMeta { return cached }
        let url = appSupportDir.appendingPathComponent("schematics_metadata.json")
        guard FileManager.default.fileExists(atPath: url.path) else {
            return [:]
        }
        let data  = try Data(contentsOf: url)
        let items = try decoder.decode([SchematicMeta].self, from: data)
        let dict  = Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0) })
        _schematicMeta = dict
        return dict
    }

    public func fetchSchematicMeta(for id: Int) throws -> SchematicMeta? {
        try fetchSchematicMeta()[id]
    }

    /// Create a new Project + BOM from a schematic's OCR metadata.
    /// Returns the created project.
    public func createProjectFromSchematic(
        _ schematic: Schematic,
        meta: SchematicMeta,
        status: String = "design"
    ) throws -> (Project, [BOMItem]) {
        let name = (schematic.fileName as NSString).deletingPathExtension
        let form = ProjectForm(
            name:        name,
            effectType:  schematic.effectType ?? schematic.categoryFolder.components(separatedBy: " ").first?.lowercased() ?? "",
            status:      status,
            description: "Created from schematic: \(schematic.categoryFolder)",
            notes:       "Source: \(schematic.filePath)"
        )
        let project = try addProject(form)

        var created: [BOMItem] = []
        for entry in meta.bomEntries {
            var itemForm = BOMItemForm()
            itemForm.category   = entry.category
            itemForm.value      = entry.value
            itemForm.quantity   = entry.quantity

            // Try to link to inventory by category + value match
            if let comps = _components {
                let match = comps.first {
                    $0.category == entry.category &&
                    $0.value.lowercased() == entry.value.lowercased()
                }
                itemForm.componentId = match?.id
            }

            let item = try addBOMItem(itemForm, projectId: project.id)
            created.append(item)
        }
        return (project, created)
    }

    // =========================================================================
    // MARK: – Supplier Listings
    // =========================================================================

    private func supplierListings() throws -> [SupplierListing] {
        if _supplierListings == nil {
            let url = dataURL("supplier_listings")
            if FileManager.default.fileExists(atPath: url.path) {
                let data = try Data(contentsOf: url)
                _supplierListings = try decoder.decode([SupplierListing].self, from: data)
            } else {
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

    public func saveSupplierListing(
        result: SupplierSearchResult,
        supplierId: Int,
        componentId: Int?
    ) throws -> SupplierListing {
        var all = try supplierListings()
        let ts  = now()

        // Replace existing listing for same supplier+component, or add new
        let existingIdx = all.firstIndex {
            $0.supplierId == supplierId &&
            ($0.componentId == componentId || ($0.componentId == nil && componentId == nil)) &&
            $0.sku == result.sku
        }

        if let idx = existingIdx {
            all[idx].price       = result.price
            all[idx].inStock     = result.inStock
            all[idx].lastChecked = ts
            let updated = all[idx]
            _supplierListings = all
            try save(all, name: "supplier_listings")
            return updated
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

    // MARK: – Private helpers

    private func makeSlug(_ name: String) -> String {
        name.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { !$0.isEmpty }
            .joined(separator: "-")
    }
}

// MARK: – Errors

public enum DataError: LocalizedError, Sendable {
    case missingResource(String)
    case notFound(Int)

    public var errorDescription: String? {
        switch self {
        case .missingResource(let n): return "Bundled resource not found: \(n).json"
        case .notFound(let id):       return "Record \(id) not found"
        }
    }
}

// MARK: – Private bundle helper (projects.json wraps both arrays)

private struct ProjectBundle: Codable, Sendable {
    let projects: [Project]
    let bomItems: [BOMItem]

    enum CodingKeys: String, CodingKey {
        case projects
        case bomItems = "bom_items"
    }
}
