import { useState } from "react";
import { Link } from "react-router-dom";
import { useProjects, useCreateProject } from "../hooks/useProjects.ts";
import Modal from "../components/Modal.tsx";
import { FolderKanban, PlusCircle } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  design: "bg-blue-100 text-blue-700",
  prototype: "bg-purple-100 text-purple-700",
  production: "bg-green-100 text-green-700",
  archived: "bg-gray-100 text-gray-500",
};

const EFFECT_TYPES = [
  "overdrive", "distortion", "fuzz", "delay", "reverb", "chorus", "flanger",
  "phaser", "tremolo", "compressor", "filter", "eq", "pitch", "synth",
  "utility", "power", "other",
];

export default function Projects() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", slug: "", effect_type: "", description: "" });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    const slug = form.slug || form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "");
    createProject.mutate(
      { ...form, slug, effect_type: form.effect_type || null, description: form.description || null },
      {
        onSuccess: () => {
          setShowCreate(false);
          setForm({ name: "", slug: "", effect_type: "", description: "" });
        },
      },
    );
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          <PlusCircle className="w-4 h-4" />
          New Project
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects?.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow block"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FolderKanban className="w-4 h-4 text-gray-400" />
                  <h3 className="font-semibold">{p.name}</h3>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[p.status] || "bg-gray-100"}`}>
                  {p.status}
                </span>
              </div>
              {p.effect_type && (
                <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded">
                  {p.effect_type}
                </span>
              )}
              {p.description && (
                <p className="text-sm text-gray-500 mt-2 line-clamp-2">{p.description}</p>
              )}
              <p className="text-xs text-gray-400 mt-3">
                Updated {new Date(p.updated_at).toLocaleDateString()}
              </p>
            </Link>
          ))}
          {projects?.length === 0 && (
            <p className="text-gray-400 col-span-full">No projects yet. Create one to get started.</p>
          )}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Project">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Project Name *</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="e.g. Klon Centaur Clone"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="auto-generated from name if blank"
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Effect Type</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={form.effect_type}
              onChange={(e) => setForm({ ...form, effect_type: e.target.value })}
            >
              <option value="">Select type...</option>
              {EFFECT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              rows={3}
              placeholder="Brief description of the project..."
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button type="submit" disabled={createProject.isPending} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              {createProject.isPending ? "Creating..." : "Create Project"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
