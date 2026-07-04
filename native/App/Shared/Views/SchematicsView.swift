// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore
#if os(macOS)
import AppKit
import PDFKit
#endif

// MARK: – Main view

public struct SchematicsView: View {
    @Environment(WorkshopStore.self) var store
    @State private var search = ""
    @State private var selectedCategory = ""

    public init() {}

    var categories: [String] {
        Array(Set(store.schematics.map(\.categoryFolder))).sorted()
    }

    var filtered: [Schematic] {
        let q = search.lowercased()
        return store.schematics.filter { s in
            (selectedCategory.isEmpty || s.categoryFolder == selectedCategory) &&
            (q.isEmpty ||
             s.fileName.lowercased().contains(q) ||
             s.categoryFolder.lowercased().contains(q) ||
             (s.effectType?.lowercased().contains(q) ?? false) ||
             (s.tags?.contains(where: { $0.lowercased().contains(q) }) ?? false))
        }
    }

    let columns = [GridItem(.adaptive(minimum: 200, maximum: 260), spacing: 12)]

    public var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 12) {
                ForEach(filtered) { schematic in
                    NavigationLink(destination: SchematicDetailView(schematic: schematic)) {
                        SchematicGridCell(schematic: schematic)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding()
        }
        .navigationTitle("Schematics (\(filtered.count))")
        .searchable(text: $search, prompt: "Search name, category…")
        .toolbar {
            ToolbarItem(placement: .automatic) {
                Picker("Category", selection: $selectedCategory) {
                    Text("All Categories").tag("")
                    ForEach(categories, id: \.self) { cat in
                        Text(cat).tag(cat)
                    }
                }
                .pickerStyle(.menu)
                .frame(maxWidth: 220)
            }
        }
        .task { if store.schematics.isEmpty { await store.loadAll() } }
    }
}

// MARK: – Grid cell

struct SchematicGridCell: View {
    let schematic: Schematic

    #if os(macOS)
    @State private var thumbnail: NSImage?
    @State private var thumbFailed = false
    #endif

    var typeColor: Color {
        switch schematic.fileType.lowercased() {
        case "pdf":        return .red
        case "gif":        return .blue
        case "png":        return .green
        case "jpg","jpeg": return .orange
        default:           return .gray
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Thumbnail area
            ZStack {
                Rectangle()
                    .fill(Color.secondary.opacity(0.08))

                #if os(macOS)
                if let img = thumbnail {
                    Image(nsImage: img)
                        .resizable()
                        .scaledToFit()
                        .padding(4)
                } else if thumbFailed {
                    // File missing/unreadable — fail loudly, not an eternal spinner.
                    VStack(spacing: 6) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 28))
                            .foregroundStyle(.orange)
                        Text("File not found")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    VStack(spacing: 8) {
                        Image(systemName: typeIcon)
                            .font(.system(size: 32))
                            .foregroundStyle(typeColor.opacity(0.5))
                        ProgressView()
                            .scaleEffect(0.7)
                    }
                }
                #endif
            }
            .frame(height: 160)
            .clipShape(UnevenRoundedRectangle(
                topLeadingRadius: 10, topTrailingRadius: 10))

            // Label area
            VStack(alignment: .leading, spacing: 4) {
                Text((schematic.fileName as NSString).deletingPathExtension)
                    .font(.caption).fontWeight(.medium)
                    .lineLimit(2)
                    .foregroundStyle(.primary)

                HStack(spacing: 4) {
                    Text(schematic.fileType.uppercased())
                        .font(.system(size: 9, weight: .bold))
                        .padding(.horizontal, 4).padding(.vertical, 2)
                        .background(typeColor.opacity(0.15))
                        .foregroundStyle(typeColor)
                        .clipShape(RoundedRectangle(cornerRadius: 3))

                    Text(schematic.categoryFolder)
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 6)
        }
        .background(.background.secondary)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.06), radius: 3, y: 1)
        #if os(macOS)
        .task {
            if thumbnail == nil {
                thumbnail = await SchematicImageLoader.shared.thumbnail(for: schematic)
                if thumbnail == nil { thumbFailed = true }
            }
        }
        .contextMenu {
            Button("Open") { openFile() }
            Button("Reveal in Finder") { revealInFinder() }
        }
        #endif
    }

    private var typeIcon: String {
        switch schematic.fileType.lowercased() {
        case "pdf":        return "doc.richtext"
        case "gif":        return "photo"
        case "png":        return "photo"
        case "jpg","jpeg": return "photo"
        default:           return "doc"
        }
    }

    #if os(macOS)
    private func openFile() {
        NSWorkspace.shared.open(URL(fileURLWithPath: schematic.filePath))
    }
    private func revealInFinder() {
        NSWorkspace.shared.activateFileViewerSelecting(
            [URL(fileURLWithPath: schematic.filePath)])
    }
    #endif
}

// MARK: – Detail view

struct SchematicDetailView: View {
    @Environment(WorkshopStore.self) var store
    let schematic: Schematic

    #if os(macOS)
    @State private var image: NSImage?
    @State private var loadFailed = false
    @State private var zoom: CGFloat = 1.0
    private let minZoom: CGFloat = 0.25
    private let maxZoom: CGFloat = 8.0
    private var isPDF: Bool { schematic.fileType.lowercased() == "pdf" }
    private var fileExists: Bool { FileManager.default.fileExists(atPath: schematic.filePath) }
    #endif

    @State private var meta: SchematicMeta?
    @State private var metaLoaded = false
    @State private var showBOM = false
    @State private var creatingProject = false
    @State private var showCreatedAlert = false

    var body: some View {
        HSplitView {
            // ── Left: image viewer ──────────────────────────────────────
            Group {
                #if os(macOS)
                if isPDF, fileExists {
                    // Vector-sharp zoom + multi-page navigation via PDFKit —
                    // the raster path only ever showed page 1 at ~800 px.
                    SchematicPDFViewer(
                        url: URL(fileURLWithPath: schematic.filePath),
                        zoom: $zoom
                    )
                } else if let img = image {
                    ScrollView([.horizontal, .vertical]) {
                        Image(nsImage: img)
                            .resizable()
                            .scaledToFit()
                            // NB: no .scaleEffect here — the explicit frame IS the
                            // zoom. Stacking both drew at zoom² and clipped.
                            .frame(
                                width:  img.size.width  * zoom,
                                height: img.size.height * zoom
                            )
                            .padding()
                    }
                    .gesture(
                        MagnificationGesture()
                            .onChanged { v in
                                zoom = min(maxZoom, max(minZoom, zoom * v))
                            }
                    )
                } else if loadFailed || !fileExists {
                    ContentUnavailableView {
                        Label("File not found", systemImage: "exclamationmark.triangle")
                    } description: {
                        Text(schematic.filePath)
                            .font(.caption)
                            .textSelection(.enabled)
                    } actions: {
                        Button("Reveal in Finder") {
                            NSWorkspace.shared.activateFileViewerSelecting(
                                [URL(fileURLWithPath: schematic.filePath)])
                        }
                    }
                } else {
                    ProgressView("Loading…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                #else
                Text("Image viewer is macOS only.")
                #endif
            }
            .frame(minWidth: 400)

            // ── Right: BOM panel ────────────────────────────────────────
            if showBOM {
                BOMPanel(
                    schematic: schematic,
                    meta: meta,
                    metaLoaded: metaLoaded,
                    creatingProject: $creatingProject,
                    onCreateProject: {
                        creatingProject = true
                        Task {
                            await store.createProjectFromSchematic(schematic)
                            creatingProject = false
                            showCreatedAlert = true
                        }
                    }
                )
                .frame(width: 280)
            }
        }
        .navigationTitle((schematic.fileName as NSString).deletingPathExtension)
        .toolbar {
            #if os(macOS)
            ToolbarItemGroup {
                // Zoom
                Button { zoom = max(minZoom, zoom / 1.4) } label: {
                    Image(systemName: "minus.magnifyingglass")
                }.keyboardShortcut("-", modifiers: .command)

                Text("\(Int(zoom * 100))%")
                    .font(.system(.caption, design: .monospaced))
                    .frame(width: 44)

                Button { zoom = min(maxZoom, zoom * 1.4) } label: {
                    Image(systemName: "plus.magnifyingglass")
                }.keyboardShortcut("=", modifiers: .command)

                Button { zoom = 1.0 } label: {
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                }.help("Reset zoom")

                Divider()

                // BOM toggle
                Button {
                    showBOM.toggle()
                } label: {
                    Label("Parts List", systemImage: "list.bullet.rectangle")
                }
                .help(showBOM ? "Hide parts panel" : "Show extracted parts")
                .keyboardShortcut("b", modifiers: .command)

                Divider()

                Button("Open in Preview") {
                    NSWorkspace.shared.open(URL(fileURLWithPath: schematic.filePath))
                }
                Button("Reveal in Finder") {
                    NSWorkspace.shared.activateFileViewerSelecting(
                        [URL(fileURLWithPath: schematic.filePath)])
                }
            }
            #endif
        }
        #if os(macOS)
        .task {
            async let metaTask: SchematicMeta? = store.schematicMeta(for: schematic)
            if !isPDF {
                // PDFs render via PDFKit directly; only raster files need loading.
                image = await SchematicImageLoader.shared.fullImage(for: schematic)
                if image == nil { loadFailed = true }
            }
            meta = await metaTask
            metaLoaded = true
        }
        #endif
        .alert("Project Created", isPresented: $showCreatedAlert) {
            Button("OK") {
                store.lastCreatedProjectName = nil
            }
        } message: {
            if let name = store.lastCreatedProjectName {
                Text("\"\(name)\" added to Projects with \(meta?.bomCount ?? 0) BOM items.")
            }
        }
    }
}

// MARK: – BOM side panel

private struct BOMPanel: View {
    @Environment(WorkshopStore.self) var store
    let schematic: Schematic
    let meta: SchematicMeta?
    let metaLoaded: Bool
    @Binding var creatingProject: Bool
    let onCreateProject: () -> Void

    var categoryGroups: [(String, [OCRBOMEntry])] {
        guard let entries = meta?.bomEntries else { return [] }
        let order = ["resistor","capacitor","ic","transistor","diode",
                     "potentiometer","switch","jack","other"]
        var grouped: [String: [OCRBOMEntry]] = [:]
        for e in entries { grouped[e.category, default: []].append(e) }
        return order.compactMap { cat in
            guard let items = grouped[cat], !items.isEmpty else { return nil }
            return (cat, items)
        }
    }

    var alreadyHasProject: Bool {
        let title = (schematic.fileName as NSString).deletingPathExtension
        return store.projects.contains { $0.name.lowercased() == title.lowercased() }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Text("Extracted Parts")
                    .font(.headline)
                Spacer()
                if let n = meta?.bomCount, n > 0 {
                    Text("\(n) parts")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)

            Divider()

            if !metaLoaded {
                ProgressView("Analyzing…")
                    .padding()
            } else if meta == nil || meta?.bomCount == 0 {
                VStack(spacing: 8) {
                    Image(systemName: "doc.questionmark")
                        .font(.title2)
                        .foregroundStyle(.secondary)
                    Text("No parts extracted")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Text("OCR couldn't read component values from this schematic.")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity)
                .padding()
            } else {
                // BOM list
                List {
                    ForEach(categoryGroups, id: \.0) { cat, entries in
                        Section(cat.capitalized) {
                            ForEach(entries, id: \.value) { entry in
                                BOMEntryRow(entry: entry, components: store.components)
                            }
                        }
                    }
                }
                .listStyle(.inset)

                Divider()

                // Create project button
                VStack(spacing: 6) {
                    if alreadyHasProject {
                        Label("Project already exists", systemImage: "checkmark.circle.fill")
                            .font(.caption)
                            .foregroundStyle(.green)
                    } else {
                        Button {
                            onCreateProject()
                        } label: {
                            if creatingProject {
                                ProgressView()
                                    .scaleEffect(0.7)
                                    .frame(maxWidth: .infinity)
                            } else {
                                Label("Add All Parts to New Project",
                                      systemImage: "folder.badge.plus")
                                    .frame(maxWidth: .infinity)
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(creatingProject)
                        .padding(.horizontal, 8)
                    }

                    if let err = store.error {
                        Text(err).font(.caption2).foregroundStyle(.red)
                            .padding(.horizontal, 8)
                    }
                }
                .padding(.vertical, 8)
            }
        }
        .background(.background.secondary)
    }
}

// MARK: – BOM entry row with inventory status

private struct BOMEntryRow: View {
    let entry: OCRBOMEntry
    let components: [Component]

    var matched: Component? {
        components.first {
            $0.category == entry.category &&
            $0.value.lowercased() == entry.value.lowercased()
        }
    }

    var body: some View {
        HStack(spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.value)
                    .font(.system(.body, design: .monospaced))
                    .lineLimit(1)
                if let qty = matched.map({ $0.quantity }) {
                    Text("\(qty) in stock")
                        .font(.caption2)
                        .foregroundStyle(qty >= entry.quantity ? .green : .orange)
                } else {
                    Text("not in inventory")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
            Spacer()
            // Stock indicator dot
            if let comp = matched {
                Circle()
                    .fill(comp.quantity >= entry.quantity ? Color.green : Color.orange)
                    .frame(width: 7, height: 7)
            } else {
                Circle()
                    .fill(Color.secondary.opacity(0.3))
                    .frame(width: 7, height: 7)
            }
        }
        .padding(.vertical, 1)
    }
}

// MARK: – PDFKit viewer (macOS)

#if os(macOS)
/// Wraps PDFKit's PDFView for vector-sharp zooming and multi-page navigation.
/// zoom is expressed relative to fit-to-window: 1.0 = fit, 2.0 = 200% of fit.
private struct SchematicPDFViewer: NSViewRepresentable {
    let url: URL
    @Binding var zoom: CGFloat

    func makeNSView(context: Context) -> PDFView {
        let view = PDFView()
        view.document = PDFDocument(url: url)
        view.autoScales = true
        view.displayMode = .singlePageContinuous
        view.backgroundColor = .windowBackgroundColor
        DispatchQueue.main.async {
            context.coordinator.baseScale = view.scaleFactorForSizeToFit
        }
        return view
    }

    func updateNSView(_ view: PDFView, context: Context) {
        let base = context.coordinator.baseScale > 0
            ? context.coordinator.baseScale
            : view.scaleFactorForSizeToFit
        guard base > 0 else { return }
        let target = base * zoom
        if abs(view.scaleFactor - target) > 0.01 {
            view.scaleFactor = target
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }
    final class Coordinator { var baseScale: CGFloat = 0 }
}
#endif
