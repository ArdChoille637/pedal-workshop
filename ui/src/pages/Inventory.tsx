import { useState } from "react";
import {
  useComponents,
  useCreateComponent,
  useUpdateComponent,
  useDeleteComponent,
  useAdjustQuantity,
} from "../hooks/useComponents.ts";
import type { Component } from "../api.ts";
import Modal from "../components/Modal.tsx";
import ComponentForm from "../components/ComponentForm.tsx";
import { Plus, Minus, Search, PlusCircle, Pencil, Trash2 } from "lucide-react";

const CATEGORIES = [
  "resistor", "capacitor", "ic", "transistor", "diode",
  "potentiometer", "switch", "jack", "enclosure", "hardware", "consumable",
];

export default function Inventory() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Component | null>(null);
  const [adjusting, setAdjusting] = useState<{ id: number; value: string } | null>(null);

  const params: Record<string, string> = {};
  if (search) params.q = search;
  if (category) params.category = category;

  const { data: components, isLoading } = useComponents(params);
  const createMut = useCreateComponent();
  const updateMut = useUpdateComponent();
  const deleteMut = useDeleteComponent();
  const adjustQty = useAdjustQuantity();

  const handleCreate = (data: Record<string, unknown>) => {
    createMut.mutate(data, { onSuccess: () => setShowCreate(false) });
  };

  const handleUpdate = (data: Record<string, unknown>) => {
    if (!editing) return;
    updateMut.mutate({ id: editing.id, data }, { onSuccess: () => setEditing(null) });
  };

  const handleDelete = (c: Component) => {
    if (confirm(`Delete "${c.category} ${c.value}"? This cannot be undone.`)) {
      deleteMut.mutate(c.id);
    }
  };

  const handleBulkAdjust = (id: number) => {
    if (!adjusting || adjusting.id !== id) return;
    const delta = parseInt(adjusting.value);
    if (isNaN(delta) || delta === 0) { setAdjusting(null); return; }
    adjustQty.mutate({ id, delta, reason: delta > 0 ? "restock" : "manual" }, {
      onSuccess: () => setAdjusting(null),
    });
  };

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Inventory</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          <PlusCircle className="w-4 h-4" />
          Add Component
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by value, description, MPN..."
            className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Value</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Package</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Description</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Qty</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Location</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {components?.map((c) => (
                <tr
                  key={c.id}
                  className={`hover:bg-gray-50 ${
                    c.min_quantity > 0 && c.quantity <= c.min_quantity ? "bg-amber-50" : ""
                  }`}
                >
                  <td className="px-4 py-2">
                    <span className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded">
                      {c.category}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-mono font-medium">{c.value}</td>
                  <td className="px-4 py-2 text-gray-500">{c.package || "-"}</td>
                  <td className="px-4 py-2 text-gray-500 max-w-xs truncate">
                    {c.description || "-"}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {adjusting?.id === c.id ? (
                      <form
                        className="flex items-center justify-end gap-1"
                        onSubmit={(e) => { e.preventDefault(); handleBulkAdjust(c.id); }}
                      >
                        <input
                          type="number"
                          className="w-16 border rounded px-2 py-1 text-sm text-right"
                          autoFocus
                          value={adjusting.value}
                          onChange={(e) => setAdjusting({ id: c.id, value: e.target.value })}
                          onBlur={() => handleBulkAdjust(c.id)}
                          placeholder="+/-"
                        />
                      </form>
                    ) : (
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="p-0.5 rounded hover:bg-red-100 text-red-500"
                          onClick={() => adjustQty.mutate({ id: c.id, delta: -1, reason: "manual" })}
                          title="Remove 1"
                        >
                          <Minus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          className="font-mono font-medium min-w-[2rem] text-center cursor-pointer hover:bg-gray-100 rounded px-1"
                          onClick={() => setAdjusting({ id: c.id, value: "" })}
                          title="Click to adjust by custom amount"
                        >
                          {c.quantity}
                        </button>
                        <button
                          className="p-0.5 rounded hover:bg-green-100 text-green-600"
                          onClick={() => adjustQty.mutate({ id: c.id, delta: 1, reason: "manual" })}
                          title="Add 1"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{c.location || "-"}</td>
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
                        onClick={() => setEditing(c)}
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"
                        onClick={() => handleDelete(c)}
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {components?.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                    No components found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400 mt-3">
        {components?.length || 0} components shown. Click a quantity to adjust by custom amount.
      </p>

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Component" wide>
        <ComponentForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
        />
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit Component" wide>
        {editing && (
          <ComponentForm
            initial={editing}
            onSubmit={handleUpdate}
            onCancel={() => setEditing(null)}
            loading={updateMut.isPending}
          />
        )}
      </Modal>
    </div>
  );
}
