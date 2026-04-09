import { Routes, Route, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  FolderKanban,
  Hammer,
  FileImage,
  Truck,
  Settings,
} from "lucide-react";
import Dashboard from "./pages/Dashboard.tsx";
import Inventory from "./pages/Inventory.tsx";
import Projects from "./pages/Projects.tsx";
import ProjectDetail from "./pages/ProjectDetail.tsx";
import Schematics from "./pages/Schematics.tsx";
import Suppliers from "./pages/Suppliers.tsx";
import SettingsPage from "./pages/Settings.tsx";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/inventory", icon: Package, label: "Inventory" },
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/schematics", icon: FileImage, label: "Schematics" },
  { to: "/suppliers", icon: Truck, label: "Suppliers" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

export default function App() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-56 bg-gray-900 text-gray-300 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Hammer className="w-5 h-5" />
            Pedal Workshop
          </h1>
        </div>
        <div className="flex-1 py-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? "bg-indigo-600/20 text-white border-r-2 border-indigo-500"
                    : "hover:bg-gray-800 hover:text-white"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </div>
        <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
          v0.1.0
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/schematics" element={<Schematics />} />
          <Route path="/suppliers" element={<Suppliers />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
