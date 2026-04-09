import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  useProject,
  useBOMItems,
  useUpdateProject,
  useDeleteProject,
  useAddBOMItem,
  useUpdateBOMItem,
  useDeleteBOMItem,
} from "../hooks/useProjects.ts";
import { useComponents } from "../hooks/useComponents.ts";
import type { BOMItem, Component } from "../api.ts";
import Modal from "../components/Modal.tsx";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Link as LinkIcon,
  Unlink,
  Upload,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";

const CATEGORIES = [
  "resistor", "capacitor", "ic", "transistor", "diode",
  "potentiometer", "switch", "jack", "enclosure", "hardware", "consumable",
];

const STATUS_OPTS = ["design", "prototype", "production", "archived"];

function BOMStatusBadge({ item, components }: { item: BOMItem; components: Component[] }) {
  if (!item.component_id) {
    return <span className="text-xs text-gray-400 italic">unlinked</span>;
  }
  const comp = components.find((c) => c.id === item.component_id);
  if (!comp) return <span className="text-xs text-red-500">missing</span>;
  if (comp.quantity >= item.quantity) {
    return (
      <span className="text-xs text-green-600 flex items-center gap-1">
        <Check className="w-3 h-3" /> {comp.quantity} in stock
      </span>
    );
  }
  return (
    <span className="text-xs text-amber-600 flex items-center gap-1">
      <AlertTriangle className="w-3 h-3" /> {comp.quantity}/{item.quantity}
    </span>
  );
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const projectId = parseInt(id || "0");
  const navigate = useNavigate();

  const { data: project, isLoading } = useProject(projectId);
  const { data: bomItems } = useBOMItems(projectId);
  const { data: allComponents } = useComponents();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();
  const addBOM = useAddBOMItem();
  const updateBOM = useUpdateBOMItem();
  const deleteBOM = useDeleteBOMItem();

  const [showAddBOM, setShowAddBOM] = useState(false);
  const [showLink, setShowLink] = useState<BOMItem | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState("");

  // New BOM item form
  const [newBOM, setNewBOM] = useState({
    reference: "",
    category: "resistor",
    value: "",
    quantity: "1",
    notes: "",
  });

  if (isLoading || !project) {
    return <div className="p-8 text-gray-400">Loading...</div>;
  }

  const handleDeleteProject = () => {
    if (confirm(`Delete project "${project.name}"? All BOM data will be lost.`)) {
      deleteProject.mutate(projectId, { onSuccess: () => navigate("/projects") });
    }
  };

  const handleAddBOM = (e: React.FormEvent) => {
    e.preventDefault();
    addBOM.mutate({
      projectId,
      data: { ...newBOM, quantity: parseInt(newBOM.quantity) || 1, notes: newBOM.notes || null },
    }, {
      onSuccess: () => {
        setNewBOM({ reference: "", category: "resistor", value: "", quantity: "1", notes: "" });
        setShowAddBOM(false);
      },
    });
  };

  const handleLink = (bomItem: BOMItem, componentId: number | null) => {
    updateBOM.mutate({
      projectId,
      itemId: bomItem.id,
      data: { component_id: componentId },
    }, {
      onSuccess: () => setShowLink(null),
    });
  };

  const handleCSVImport = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`/api/projects/${projectId}/bom/import`, {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      setShowImport(false);
      // Refresh BOM items
      window.location.reload();
    }
  };

  const handleSaveNotes = () => {
    updateProject.mutate({ id: projectId, data: { notes } }, {
      onSuccess: () => setEditingNotes(false),
    });
  };

  const satisfied = bomItems?.filter((b) => {
    if (!b.component_id) return false;
    const comp = allComponents?.find((c) => c.id === b.component_id);
    return comp && comp.quantity >= b.quantity;
  }).length || 0;
  const total = bomItems?.filter((b) => !b.is_optional).length || 0;

  // Find matching components for linking
  const linkCandidates = showLink && allComponents
    ? allComponents.filter((c) =>
        c.category === showLink.category ||
        c.value.toLowerCase().includes(showLink.value.toLowerCase())
      )
    : [];

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/projects" className="p-1 rounded hover:bg-gray-100">
          <ArrowLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <div className="flex items-center gap-2 mt-1">
            {project.effect_type && (
              <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded">
                {project.effect_type}
              </span>
            )}
            <select
              className="text-xs border rounded px-2 py-0.5"
              value={project.status}
              onChange={(e) => updateProject.mutate({ id: projectId, data: { status: e.target.value } })}
            >
              {STATUS_OPTS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <button
          onClick={handleDeleteProject}
          className="p-2 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
          title="Delete project"
        >
          <Trash2 className="w-5 h-5" />
        </button>
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-gray-600 mb-6">{project.description}</p>
      )}

      {/* BOM readiness bar */}
      <div className="bg-white rounded-lg border p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold">BOM Readiness</h2>
          <span className="text-sm text-gray-500">
            {satisfied}/{total} parts satisfied
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${
              satisfied === total && total > 0 ? "bg-green-500" : satisfied > 0 ? "bg-yellow-400" : "bg-gray-300"
            }`}
            style={{ width: total > 0 ? `${(satisfied / total) * 100}%` : "0%" }}
          />
        </div>
      </div>

      {/* BOM Table */}
      <div className="bg-white rounded-lg border mb-6">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Bill of Materials ({bomItems?.length || 0} items)</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
            >
              <Upload className="w-3.5 h-3.5" />
              Import CSV
            </button>
            <button
              onClick={() => setShowAddBOM(true)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Item
            </button>
          </div>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-2.5 font-medium text-gray-600">Ref</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-600">Category</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-600">Value</th>
              <th className="text-center px-4 py-2.5 font-medium text-gray-600">Qty</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-600">Stock</th>
              <th className="text-left px-4 py-2.5 font-medium text-gray-600">Notes</th>
              <th className="text-center px-4 py-2.5 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {bomItems?.map((item) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{item.reference || "-"}</td>
                <td className="px-4 py-2">
                  <span className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded">{item.category}</span>
                </td>
                <td className="px-4 py-2 font-mono font-medium">{item.value}</td>
                <td className="px-4 py-2 text-center">{item.quantity}</td>
                <td className="px-4 py-2">
                  <BOMStatusBadge item={item} components={allComponents || []} />
                </td>
                <td className="px-4 py-2 text-gray-500 text-xs max-w-[200px] truncate">{item.notes || "-"}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center justify-center gap-1">
                    {item.component_id ? (
                      <button
                        className="p-1 rounded hover:bg-gray-100 text-green-500"
                        onClick={() => handleLink(item, null)}
                        title="Unlink from inventory"
                      >
                        <Unlink className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <button
                        className="p-1 rounded hover:bg-gray-100 text-indigo-500"
                        onClick={() => setShowLink(item)}
                        title="Link to inventory component"
                      >
                        <LinkIcon className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
                      onClick={() => deleteBOM.mutate({ projectId, itemId: item.id })}
                      title="Remove from BOM"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {(!bomItems || bomItems.length === 0) && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No BOM items yet. Add components or import a CSV.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Design Notes */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Design Notes</h2>
          {editingNotes ? (
            <div className="flex gap-2">
              <button onClick={() => setEditingNotes(false)} className="p-1 rounded hover:bg-gray-100 text-gray-400">
                <X className="w-4 h-4" />
              </button>
              <button onClick={handleSaveNotes} className="p-1 rounded hover:bg-green-100 text-green-600">
                <Check className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setNotes(project.notes || ""); setEditingNotes(true); }}
              className="text-xs text-indigo-600 hover:underline"
            >
              Edit
            </button>
          )}
        </div>
        {editingNotes ? (
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            rows={8}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Design journal, ideas, notes..."
          />
        ) : (
          <div className="text-sm text-gray-600 whitespace-pre-wrap">
            {project.notes || <span className="italic text-gray-400">No notes yet. Click Edit to add design notes.</span>}
          </div>
        )}
      </div>

      {/* Add BOM Item Modal */}
      <Modal open={showAddBOM} onClose={() => setShowAddBOM(false)} title="Add BOM Item">
        <form onSubmit={handleAddBOM} className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="R1, C3, IC1"
                value={newBOM.reference}
                onChange={(e) => setNewBOM({ ...newBOM, reference: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm"
                value={newBOM.category}
                onChange={(e) => setNewBOM({ ...newBOM, category: e.target.value })}
              >
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Qty</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm"
                type="number"
                min="1"
                value={newBOM.quantity}
                onChange={(e) => setNewBOM({ ...newBOM, quantity: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Value *</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. 4.7k, TL072, 3PDT"
              required
              value={newBOM.value}
              onChange={(e) => setNewBOM({ ...newBOM, value: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. Socket this, use metal film"
              value={newBOM.notes}
              onChange={(e) => setNewBOM({ ...newBOM, notes: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setShowAddBOM(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
            <button type="submit" className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Add to BOM</button>
          </div>
        </form>
      </Modal>

      {/* Link to Inventory Modal */}
      <Modal open={!!showLink} onClose={() => setShowLink(null)} title={`Link "${showLink?.reference || showLink?.value}" to Inventory`} wide>
        {showLink && (
          <div>
            <p className="text-sm text-gray-500 mb-3">
              Looking for: <strong>{showLink.category}</strong> &mdash; <strong>{showLink.value}</strong>
            </p>
            <div className="border rounded-lg overflow-hidden max-h-80 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Category</th>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Value</th>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Package</th>
                    <th className="text-right px-3 py-2 font-medium text-gray-600">Qty</th>
                    <th className="text-center px-3 py-2 font-medium text-gray-600"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {linkCandidates.map((c) => (
                    <tr
                      key={c.id}
                      className={`hover:bg-gray-50 ${
                        c.category === showLink.category && c.value === showLink.value
                          ? "bg-green-50"
                          : ""
                      }`}
                    >
                      <td className="px-3 py-2">
                        <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{c.category}</span>
                      </td>
                      <td className="px-3 py-2 font-mono font-medium">{c.value}</td>
                      <td className="px-3 py-2 text-gray-500">{c.package || "-"}</td>
                      <td className="px-3 py-2 text-right font-mono">{c.quantity}</td>
                      <td className="px-3 py-2 text-center">
                        <button
                          onClick={() => handleLink(showLink, c.id)}
                          className="px-3 py-1 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700"
                        >
                          Link
                        </button>
                      </td>
                    </tr>
                  ))}
                  {linkCandidates.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-6 text-center text-gray-400">
                        No matching components in inventory. Add one first.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Modal>

      {/* CSV Import Modal */}
      <Modal open={showImport} onClose={() => setShowImport(false)} title="Import BOM from CSV">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Upload a CSV with columns: <code className="bg-gray-100 px-1 rounded">Reference, Category, Value, Quantity, Notes</code>
          </p>
          <input
            type="file"
            accept=".csv,.json"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleCSVImport(file);
            }}
          />
        </div>
      </Modal>
    </div>
  );
}
