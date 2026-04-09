// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

@main
struct MacApp: App {
    @State private var store = WorkshopStore.shared

    var body: some Scene {
        WindowGroup {
            MacContentView()
                .environment(store)
        }
        .windowStyle(.automatic)
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Refresh All") {
                    Task { await WorkshopStore.shared.loadAll() }
                }
                .keyboardShortcut("r", modifiers: .command)
            }
        }
    }
}

struct MacContentView: View {
    @State private var selection: String? = "dashboard"
    @State private var navPath = NavigationPath()

    var body: some View {
        NavigationSplitView {
            List(selection: $selection) {
                Label("Dashboard",  systemImage: "square.grid.2x2").tag("dashboard")
                Label("Inventory",  systemImage: "cube.box").tag("inventory")
                Label("Projects",   systemImage: "folder").tag("projects")
                Label("Schematics", systemImage: "doc.text.image").tag("schematics")
                Label("Suppliers",  systemImage: "truck.box").tag("suppliers")
                Divider()
                Label("Settings",   systemImage: "gearshape").tag("settings")
            }
            .navigationSplitViewColumnWidth(min: 180, ideal: 200)
            .listStyle(.sidebar)
        } detail: {
            NavigationStack(path: $navPath) {
                switch selection {
                case "dashboard":  DashboardView()
                case "inventory":  InventoryView()
                case "projects":   ProjectsView()
                case "schematics": SchematicsView()
                case "suppliers":  SuppliersView()
                case "settings":   SettingsView()
                default:           DashboardView()
                }
            }
            .onChange(of: selection) { navPath = NavigationPath() }
        }
        .frame(minWidth: 900, minHeight: 600)
    }
}
