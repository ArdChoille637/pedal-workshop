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

// MARK: – Detail view (image / PDF viewer)

struct SchematicDetailView: View {
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

    var body: some View {
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
            if !isPDF {
                // PDFs render via PDFKit directly; only raster files need loading.
                image = await SchematicImageLoader.shared.fullImage(for: schematic)
                if image == nil { loadFailed = true }
            }
        }
        #endif
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
