// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

struct SettingsView: View {
    @Environment(WorkshopStore.self) var store

    @State private var mouserKey: String = ""
    @State private var saved = false

    var body: some View {
        Form {
            Section {
                HStack {
                    SecureField("Mouser API Key", text: $mouserKey)
                    Link("Get key →", destination: URL(string: "https://www.mouser.com/api-hub/")!)
                        .font(.caption)
                }
                Text("Register free at mouser.com/api-hub. Required for Mouser price lookups; Tayda, Mammoth, and Love My Switches work without a key.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } header: {
                Text("Supplier API Keys")
            }

            Section {
                HStack {
                    Spacer()
                    Button("Save") {
                        store.mouserAPIKey = mouserKey
                        saved = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { saved = false }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(mouserKey == store.mouserAPIKey)

                    if saved {
                        Label("Saved", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                            .font(.caption)
                            .transition(.opacity)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .navigationTitle("Settings")
        .onAppear { mouserKey = store.mouserAPIKey }
    }
}
