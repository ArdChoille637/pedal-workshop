import SwiftUI
import WorkshopCore

// MARK: – Barcode Parser

struct ParsedBarcode: Sendable {
    var mpn: String?
    var supplierPN: String?
    var quantity: Int = 1
    var supplier: String?
    var rawValue: String

    var displayLabel: String { mpn ?? supplierPN ?? rawValue }
}

enum BarcodeParser {
    /// Parse a raw barcode string (from USB scanner or manual entry).
    /// Supports GS1-128 / MH10.8.2 (DigiKey, Mouser QR bag labels) and plain text.
    static func parse(_ raw: String) -> ParsedBarcode {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)

        // GS1/MH10.8.2 structured format: contains header "[)>" or control chars
        if trimmed.hasPrefix("[)>") || trimmed.contains("\u{1E}") || trimmed.contains("\u{1D}") {
            return parseGS1(trimmed)
        }
        // Plain part number / value string
        return ParsedBarcode(mpn: trimmed.isEmpty ? nil : trimmed, rawValue: trimmed)
    }

    private static func parseGS1(_ raw: String) -> ParsedBarcode {
        // Normalize separators: GS (0x1D), RS (0x1E), FS (0x1C), CR → newline
        var norm = raw
        for ch in ["\u{1D}", "\u{1E}", "\u{1C}", "\u{04}"] {
            norm = norm.replacingOccurrences(of: ch, with: "\n")
        }
        norm = norm.replacingOccurrences(of: "\r\n", with: "\n")
                   .replacingOccurrences(of: "\r",   with: "\n")

        var result = ParsedBarcode(rawValue: raw)

        let fields = norm.components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }

        for field in fields {
            if field.hasPrefix("30P") {
                // Mouser part number
                let val = String(field.dropFirst(3))
                if !val.isEmpty { result.supplierPN = val; result.supplier = "Mouser" }
            } else if field.hasPrefix("1P") {
                // DigiKey / supplier PN
                let val = String(field.dropFirst(2))
                if !val.isEmpty {
                    result.supplierPN = val
                    if val.hasSuffix("-ND") || val.hasSuffix("-1-ND") {
                        result.supplier = "DigiKey"
                    }
                }
            } else if field.hasPrefix("P") {
                // Customer PN / MPN
                let val = String(field.dropFirst())
                if !val.isEmpty { result.mpn = val }
            } else if field.hasPrefix("Q") {
                if let qty = Int(field.dropFirst()), qty > 0 { result.quantity = qty }
            } else if field.hasPrefix("11Z") {
                if let qty = Int(field.dropFirst(3)), qty > 0 { result.quantity = qty }
            }
        }
        return result
    }
}

// MARK: – Scanned item model

struct ScannedItem: Identifiable, Sendable {
    let id: UUID = UUID()
    let barcode: ParsedBarcode
    let matchedId: Int?          // Component.id, if matched
    let matchedValue: String?
    let matchedCategory: String?
    let matchedStock: Int?
    var quantityToAdd: Int
    var applied: Bool = false
}

// MARK: – Main view

struct BarcodeEntryView: View {
    @Environment(WorkshopStore.self) var store
    @Environment(\.dismiss) var dismiss

    @State private var inputText  = ""
    @State private var items: [ScannedItem] = []
    @State private var addNewBarcode: ParsedBarcode? = nil   // triggers ComponentFormView sheet
    @FocusState private var fieldFocused: Bool

    private var pendingWithMatch: [ScannedItem] { items.filter { !$0.applied && $0.matchedId != nil } }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                inputSection
                Divider()
                if items.isEmpty { emptyState } else { itemList }
            }
            .navigationTitle("Barcode / Scanner Entry")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Done") { dismiss() }
                }
                ToolbarItem(placement: .primaryAction) {
                    if !pendingWithMatch.isEmpty {
                        Button("Apply All (\(pendingWithMatch.count))") { applyAll() }
                    }
                }
            }
        }
        .onAppear { fieldFocused = true }
        .sheet(item: $addNewBarcode) { bc in
            ComponentFormView(fromBarcode: bc)
                .environment(store)
        }
        .frame(minWidth: 580, minHeight: 500)
    }

    // MARK: – Input section

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Scan a barcode or type a part number / value",
                  systemImage: "barcode.viewfinder")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(spacing: 8) {
                TextField("Waiting for scan…", text: $inputText)
                    .textFieldStyle(.plain)
                    .font(.system(.body, design: .monospaced))
                    .focused($fieldFocused)
                    .onSubmit { process() }

                if !inputText.isEmpty {
                    Button { inputText = "" } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }

                Button { process() } label: {
                    Label("Scan", systemImage: "barcode")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding(10)
            .background(.background.secondary)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Text("USB barcode scanners work automatically — just scan and the field captures the input. DigiKey and Mouser QR bag labels include quantity automatically.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding()
    }

    // MARK: – Empty state

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "barcode.viewfinder")
                .font(.system(size: 52))
                .foregroundStyle(.secondary)
            Text("Ready to scan")
                .font(.title3).fontWeight(.medium)
            Text("Scan a DigiKey or Mouser bag label to auto-extract part + quantity,\nor type any part number or component value.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: – Item list

    private var itemList: some View {
        List {
            ForEach(items.indices, id: \.self) { i in
                ScannedItemRow(item: $items[i]) {
                    apply(at: i)
                } onAddNew: {
                    addNewBarcode = items[i].barcode
                }
            }
        }
        .listStyle(.inset)
    }

    // MARK: – Logic

    private func process() {
        let raw = inputText.trimmingCharacters(in: .whitespaces)
        guard !raw.isEmpty else { return }

        let parsed = BarcodeParser.parse(raw)

        // Match by MPN first, then by value
        let comp = store.components.first { c in
            if let mpn = parsed.mpn, let cMPN = c.mpn {
                return mpn.lowercased() == cMPN.lowercased()
            }
            if let mpn = parsed.mpn {
                return c.value.lowercased() == mpn.lowercased()
            }
            return false
        }

        let item = ScannedItem(
            barcode:          parsed,
            matchedId:        comp?.id,
            matchedValue:     comp?.value,
            matchedCategory:  comp?.category,
            matchedStock:     comp?.quantity,
            quantityToAdd:    parsed.quantity
        )
        items.insert(item, at: 0)
        inputText   = ""
        fieldFocused = true
    }

    private func apply(at index: Int) {
        guard !items[index].applied, let compId = items[index].matchedId else { return }
        let qty = items[index].quantityToAdd
        items[index].applied = true
        Task {
            if let comp = store.components.first(where: { $0.id == compId }) {
                await store.adjustQuantity(component: comp, delta: qty)
            }
        }
    }

    private func applyAll() {
        for i in items.indices where !items[i].applied && items[i].matchedId != nil {
            apply(at: i)
        }
    }
}

// MARK: – Scanned item row

struct ScannedItemRow: View {
    @Binding var item: ScannedItem
    let onApply:   () -> Void
    let onAddNew:  () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(dotColor)
                .frame(width: 8, height: 8)

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(item.barcode.displayLabel)
                        .font(.system(.body, design: .monospaced))
                        .fontWeight(.medium)
                        .lineLimit(1)
                    if let sup = item.barcode.supplier {
                        Text(sup)
                            .font(.system(size: 9, weight: .bold))
                            .padding(.horizontal, 4).padding(.vertical, 2)
                            .background(Color.blue.opacity(0.12))
                            .foregroundStyle(.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 3))
                    }
                }
                if let mv = item.matchedValue, let mc = item.matchedCategory {
                    Text("Matched: \(mv) · \(mc) · \(item.matchedStock ?? 0) in stock")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text("No inventory match")
                        .font(.caption).foregroundStyle(.orange)
                }
                if let spn = item.barcode.supplierPN, spn != item.barcode.mpn {
                    Text("Supplier PN: \(spn)")
                        .font(.caption2).foregroundStyle(.tertiary)
                }
            }

            Spacer()

            if item.applied {
                Label("Applied", systemImage: "checkmark.circle.fill")
                    .font(.caption).foregroundStyle(.green)
            } else {
                // Quantity stepper
                HStack(spacing: 4) {
                    Button {
                        if item.quantityToAdd > 1 { item.quantityToAdd -= 1 }
                    } label: { Image(systemName: "minus.circle") }
                    .buttonStyle(.borderless)

                    Text("+\(item.quantityToAdd)")
                        .font(.system(.body, design: .monospaced))
                        .frame(minWidth: 40, alignment: .center)

                    Button { item.quantityToAdd += 1 } label: {
                        Image(systemName: "plus.circle")
                    }
                    .buttonStyle(.borderless)
                }

                if item.matchedId != nil {
                    Button("Apply", action: onApply)
                        .buttonStyle(.borderedProminent)
                        .controlSize(.small)
                } else {
                    Button("Add New", action: onAddNew)
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                }
            }
        }
        .padding(.vertical, 4)
        .opacity(item.applied ? 0.55 : 1.0)
    }

    private var dotColor: Color {
        if item.applied    { return .green }
        if item.matchedId != nil { return .blue }
        return .orange
    }
}

// MARK: – ParsedBarcode: Identifiable (for sheet binding)
extension ParsedBarcode: Identifiable {
    var id: String { supplierPN ?? mpn ?? rawValue }
}
