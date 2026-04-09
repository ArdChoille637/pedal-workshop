// macOS-only: thumbnail loading for GIF / JPG / PNG / PDF schematics.
#if os(macOS)
import AppKit
import PDFKit
import WorkshopCore

/// Async thumbnail loader with NSCache. Each cell calls thumbnail(for:) on appear;
/// LazyVGrid ensures only visible cells trigger loads.
actor SchematicImageLoader {
    static let shared = SchematicImageLoader()

    private let cache: NSCache<NSString, NSImage> = {
        let c = NSCache<NSString, NSImage>()
        c.totalCostLimit = 64 * 1024 * 1024   // 64 MB cap
        return c
    }()

    private init() {}

    // MARK: – Public

    /// Returns a thumbnail for display in the grid (~300 pt wide).
    func thumbnail(for schematic: Schematic) async -> NSImage? {
        let key = NSString(string: schematic.filePath)
        if let hit = cache.object(forKey: key) { return hit }

        let url = URL(fileURLWithPath: schematic.filePath)
        guard let raw = await load(url: url, type: schematic.fileType) else { return nil }

        let thumb = scaled(raw, maxDimension: 360)
        let cost  = Int(thumb.size.width * thumb.size.height * 4)
        cache.setObject(thumb, forKey: key, cost: cost)
        return thumb
    }

    /// Full-resolution image for the detail view.
    func fullImage(for schematic: Schematic) async -> NSImage? {
        let url = URL(fileURLWithPath: schematic.filePath)
        return await load(url: url, type: schematic.fileType)
    }

    // MARK: – Private

    private func load(url: URL, type: String) async -> NSImage? {
        switch type.lowercased() {
        case "pdf":
            return renderPDF(url: url)
        default:
            // NSImage handles GIF, JPG, PNG natively
            return NSImage(contentsOf: url)
        }
    }

    private func renderPDF(url: URL) -> NSImage? {
        guard let doc  = PDFDocument(url: url),
              let page = doc.page(at: 0) else { return nil }
        let bounds = page.bounds(for: .mediaBox)
        guard bounds.width > 0, bounds.height > 0 else { return nil }
        // Render at 2× a 400-pt-wide thumbnail
        let scale   = (400 * 2) / max(bounds.width, bounds.height)
        let size    = NSSize(width: bounds.width * scale, height: bounds.height * scale)
        return page.thumbnail(of: size, for: .mediaBox)
    }

    private func scaled(_ image: NSImage, maxDimension: CGFloat) -> NSImage {
        let src = image.size
        guard src.width > 0, src.height > 0 else { return image }
        let scale  = min(maxDimension / src.width, maxDimension / src.height, 1.0)
        let dst    = NSSize(width: src.width * scale, height: src.height * scale)
        let result = NSImage(size: dst)
        result.lockFocus()
        image.draw(in: CGRect(origin: .zero, size: dst),
                   from: CGRect(origin: .zero, size: src),
                   operation: .copy, fraction: 1.0)
        result.unlockFocus()
        return result
    }
}
#endif
