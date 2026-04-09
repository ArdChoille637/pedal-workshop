import SwiftUI
import WorkshopCore

public struct ProjectsView: View {
    @Environment(WorkshopStore.self) var store
    @State private var showingAdd = false

    public init() {}

    public var body: some View {
        Group {
            if store.projects.isEmpty && store.isLoading {
                ProgressView("Loading projects…").frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if store.projects.isEmpty {
                ContentUnavailableView("No projects", systemImage: "folder",
                    description: Text("Tap + to create your first pedal project."))
            } else {
                List(store.projects) { project in
                    ProjectListItem(project: project)
                }
            }
        }
        .navigationTitle("Projects")
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingAdd = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingAdd) {
            ProjectFormView()
                .environment(store)
        }
        .refreshable { await store.loadProjects() }
        .task { if store.projects.isEmpty { await store.loadProjects() } }
    }
}

// MARK: – Project List Item (owns edit/delete state for swipe + context menu)

private struct ProjectListItem: View {
    @Environment(WorkshopStore.self) var store
    let project: Project
    @State private var showingEdit = false
    @State private var showingDeleteConfirm = false

    var body: some View {
        NavigationLink(destination: ProjectDetailView(project: project)) {
            ProjectRow(project: project)
        }
        .swipeActions(edge: .leading, allowsFullSwipe: false) {
            Button { showingEdit = true } label: {
                Label("Edit", systemImage: "pencil")
            }.tint(.blue)
        }
        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
            Button(role: .destructive) { showingDeleteConfirm = true } label: {
                Label("Delete", systemImage: "trash")
            }
        }
        .contextMenu {
            Button("Edit") { showingEdit = true }
            Divider()
            Button("Delete", role: .destructive) { showingDeleteConfirm = true }
        }
        .sheet(isPresented: $showingEdit) {
            ProjectFormView(editing: project).environment(store)
        }
        .confirmationDialog(
            "Delete \"\(project.name)\"?",
            isPresented: $showingDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task { await store.deleteProject(project) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This also deletes all BOM items for this project.")
        }
    }
}

// MARK: – Swipe action helpers (need store access)

private struct EditProjectButton: View {
    @Environment(WorkshopStore.self) var store
    let project: Project
    @State private var showingEdit = false

    var body: some View {
        Button {
            showingEdit = true
        } label: {
            Label("Edit", systemImage: "pencil")
        }
        .tint(.blue)
        .sheet(isPresented: $showingEdit) {
            ProjectFormView(editing: project)
                .environment(store)
        }
    }
}

private struct DeleteProjectButton: View {
    @Environment(WorkshopStore.self) var store
    let project: Project
    @State private var showingConfirm = false

    var body: some View {
        Button(role: .destructive) {
            showingConfirm = true
        } label: {
            Label("Delete", systemImage: "trash")
        }
        .confirmationDialog(
            "Delete \"\(project.name)\"?",
            isPresented: $showingConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task { await store.deleteProject(project) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will also delete all BOM items for this project.")
        }
    }
}

// MARK: – Project Row

struct ProjectRow: View {
    let project: Project

    var statusColor: Color {
        switch project.status {
        case "design":         return .blue
        case "prototype":      return .purple
        case "parts_sourcing": return .yellow
        case "production":     return .green
        case "complete":       return .teal
        case "archived":       return .gray
        default:               return .gray
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(project.name).font(.headline)
                Spacer()
                Text(project.status.replacingOccurrences(of: "_", with: " "))
                    .font(.caption2).padding(.horizontal, 6).padding(.vertical, 2)
                    .background(statusColor.opacity(0.15))
                    .foregroundStyle(statusColor)
                    .clipShape(Capsule())
            }
            if let et = project.effectType {
                Text(et).font(.caption).foregroundStyle(.indigo)
            }
            if let desc = project.description {
                Text(desc).font(.caption).foregroundStyle(.secondary).lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: – Project Detail

struct ProjectDetailView: View {
    @Environment(WorkshopStore.self) var store
    let project: Project
    @State private var bomItems: [BOMItem] = []
    @State private var loading = true
    @State private var showingAddBOM = false

    var body: some View {
        List {
            Section("Info") {
                if let et = project.effectType {
                    LabeledContent("Effect Type", value: et)
                }
                LabeledContent("Status",
                    value: project.status.replacingOccurrences(of: "_", with: " "))
                if let desc = project.description {
                    Text(desc).foregroundStyle(.secondary)
                }
            }

            Section("Bill of Materials (\(bomItems.count))") {
                if loading {
                    ProgressView()
                } else if bomItems.isEmpty {
                    Text("No BOM items").foregroundStyle(.secondary)
                } else {
                    ForEach(bomItems) { item in
                        HStack {
                            if let ref = item.reference {
                                Text(ref)
                                    .font(.system(.caption, design: .monospaced))
                                    .foregroundStyle(.secondary)
                                    .frame(width: 40, alignment: .leading)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text(item.value)
                                    .font(.system(.body, design: .monospaced))
                                Text(item.category).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            bomStatusView(item)
                        }
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button(role: .destructive) {
                                Task {
                                    await store.deleteBOMItem(item)
                                    bomItems.removeAll { $0.id == item.id }
                                }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                }
            }

            if let notes = project.notes, !notes.isEmpty {
                Section("Design Notes") {
                    Text(notes).font(.body).foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle(project.name)
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                Button {
                    showingAddBOM = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingAddBOM) {
            BOMItemFormView(project: project)
                .environment(store)
                .onDisappear {
                    Task { await reloadBOM() }
                }
        }
        .task {
            await reloadBOM()
        }
    }

    private func reloadBOM() async {
        loading = true
        bomItems = (try? await LocalDataStore.shared.fetchBOMItems(projectId: project.id)) ?? []
        loading = false
    }

    @ViewBuilder
    private func bomStatusView(_ item: BOMItem) -> some View {
        // Try direct component link first, then fall back to category+value match
        let matched: Component? = {
            if let cid = item.componentId,
               let comp = store.components.first(where: { $0.id == cid }) {
                return comp
            }
            return store.components.first {
                $0.category == item.category &&
                $0.value.lowercased() == item.value.lowercased()
            }
        }()

        if let comp = matched {
            HStack(spacing: 4) {
                Circle()
                    .fill(comp.quantity >= item.quantity ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)
                Text("\(comp.quantity)")
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(comp.quantity >= item.quantity ? .green : .orange)
            }
        } else {
            Text("unlinked").font(.caption2).foregroundStyle(.tertiary)
        }
    }
}
