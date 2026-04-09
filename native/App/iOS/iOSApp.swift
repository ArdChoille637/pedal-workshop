import SwiftUI
import WorkshopCore

@main
struct iOSApp: App {
    @State private var store = WorkshopStore.shared

    var body: some Scene {
        WindowGroup {
            iOSContentView()
                .environment(store)
        }
    }
}

struct iOSContentView: View {
    var body: some View {
        TabView {
            NavigationStack { DashboardView() }
                .tabItem { Label("Dashboard", systemImage: "square.grid.2x2") }

            NavigationStack { InventoryView() }
                .tabItem { Label("Inventory", systemImage: "cube.box") }

            NavigationStack { ProjectsView() }
                .tabItem { Label("Projects", systemImage: "folder") }

            NavigationStack { SchematicsView() }
                .tabItem { Label("Schematics", systemImage: "doc.text.image") }

            NavigationStack { SuppliersView() }
                .tabItem { Label("Suppliers", systemImage: "truck.box") }
        }
    }
}
