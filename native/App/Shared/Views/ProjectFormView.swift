import SwiftUI
import WorkshopCore

private let kEffectTypes = [
    "overdrive", "distortion", "fuzz", "delay", "reverb",
    "chorus", "flanger", "phaser", "compressor", "tremolo",
    "vibrato", "wah", "filter", "boost", "eq", "other"
]

private let kStatuses = [
    "design", "prototype", "parts_sourcing", "production", "complete", "archived"
]

public struct ProjectFormView: View {
    @Environment(WorkshopStore.self) var store
    @Environment(\.dismiss) var dismiss

    let editing: Project?

    @State private var form: ProjectForm
    @State private var saving = false
    @State private var errorMessage: String?

    // Add mode
    public init() {
        editing = nil
        _form = State(initialValue: ProjectForm())
    }

    // Edit mode
    public init(editing project: Project) {
        editing = project
        _form = State(initialValue: ProjectForm(from: project))
    }

    public var body: some View {
        NavigationStack {
            Form {
                Section("Project") {
                    TextField("Name", text: $form.name)
                    Picker("Effect Type", selection: $form.effectType) {
                        Text("(none)").tag("")
                        ForEach(kEffectTypes, id: \.self) { et in
                            Text(et.capitalized).tag(et)
                        }
                    }
                    Picker("Status", selection: $form.status) {
                        ForEach(kStatuses, id: \.self) { s in
                            Text(s.replacingOccurrences(of: "_", with: " ").capitalized).tag(s)
                        }
                    }
                }

                Section("Description") {
                    TextEditor(text: $form.description)
                        .frame(minHeight: 80)
                }

                Section("Notes") {
                    TextEditor(text: $form.notes)
                        .frame(minHeight: 80)
                }

                if let msg = errorMessage {
                    Section {
                        Text(msg).foregroundStyle(.red).font(.caption)
                    }
                }
            }
            .navigationTitle(editing == nil ? "Add Project" : "Edit Project")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") { save() }
                        .disabled(form.name.trimmingCharacters(in: .whitespaces).isEmpty || saving)
                }
            }
        }
    }

    private func save() {
        saving = true
        Task {
            if let existing = editing {
                var updated = existing
                updated.name        = form.name
                updated.effectType  = form.effectType.nilIfEmpty
                updated.status      = form.status
                updated.description = form.description.nilIfEmpty
                updated.notes       = form.notes.nilIfEmpty
                await store.updateProject(updated)
            } else {
                await store.addProject(form)
            }
            dismiss()
        }
    }
}
