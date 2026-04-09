import { useState } from "react";
import type { Component } from "../api.ts";

const CATEGORIES = [
  "resistor", "capacitor", "ic", "transistor", "diode",
  "potentiometer", "switch", "jack", "enclosure", "hardware", "consumable",
];

interface ComponentFormProps {
  initial?: Partial<Component>;
  onSubmit: (data: Record<string, unknown>) => void;
  onCancel: () => void;
  loading?: boolean;
}

export default function ComponentForm({ initial, onSubmit, onCancel, loading }: ComponentFormProps) {
  const [form, setForm] = useState({
    category: initial?.category || "resistor",
    subcategory: initial?.subcategory || "",
    value: initial?.value || "",
    value_numeric: initial?.value_numeric?.toString() || "",
    value_unit: initial?.value_unit || "",
    package: initial?.package || "",
    description: initial?.description || "",
    manufacturer: initial?.manufacturer || "",
    mpn: initial?.mpn || "",
    quantity: initial?.quantity?.toString() || "0",
    min_quantity: initial?.min_quantity?.toString() || "0",
    location: initial?.location || "",
    notes: initial?.notes || "",
  });

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      ...form,
      value_numeric: form.value_numeric ? parseFloat(form.value_numeric) : null,
      quantity: parseInt(form.quantity) || 0,
      min_quantity: parseInt(form.min_quantity) || 0,
      subcategory: form.subcategory || null,
      value_unit: form.value_unit || null,
      package: form.package || null,
      description: form.description || null,
      manufacturer: form.manufacturer || null,
      mpn: form.mpn || null,
      location: form.location || null,
      notes: form.notes || null,
    });
  };

  const inputCls = "w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500";
  const labelCls = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Category *</label>
          <select className={inputCls} value={form.category} onChange={(e) => set("category", e.target.value)} required>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls}>Subcategory</label>
          <input className={inputCls} placeholder="e.g. metal_film, ceramic" value={form.subcategory} onChange={(e) => set("subcategory", e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className={labelCls}>Value *</label>
          <input className={inputCls} placeholder="e.g. 4.7k, TL072" value={form.value} onChange={(e) => set("value", e.target.value)} required />
        </div>
        <div>
          <label className={labelCls}>Numeric Value</label>
          <input className={inputCls} type="number" step="any" placeholder="4700" value={form.value_numeric} onChange={(e) => set("value_numeric", e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>Unit</label>
          <input className={inputCls} placeholder="ohm, farad" value={form.value_unit} onChange={(e) => set("value_unit", e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Package</label>
          <input className={inputCls} placeholder="e.g. DIP-8, TO-92, axial" value={form.package} onChange={(e) => set("package", e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>Location</label>
          <input className={inputCls} placeholder="e.g. Drawer A3, Bin 12" value={form.location} onChange={(e) => set("location", e.target.value)} />
        </div>
      </div>

      <div>
        <label className={labelCls}>Description</label>
        <input className={inputCls} placeholder="e.g. 1/4W metal film" value={form.description} onChange={(e) => set("description", e.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Manufacturer</label>
          <input className={inputCls} placeholder="e.g. Texas Instruments" value={form.manufacturer} onChange={(e) => set("manufacturer", e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>MPN</label>
          <input className={inputCls} placeholder="Manufacturer part number" value={form.mpn} onChange={(e) => set("mpn", e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelCls}>Quantity on Hand</label>
          <input className={inputCls} type="number" min="0" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} />
        </div>
        <div>
          <label className={labelCls}>Min Quantity (reorder alert)</label>
          <input className={inputCls} type="number" min="0" value={form.min_quantity} onChange={(e) => set("min_quantity", e.target.value)} />
        </div>
      </div>

      <div>
        <label className={labelCls}>Notes</label>
        <textarea className={inputCls} rows={2} placeholder="Any notes..." value={form.notes} onChange={(e) => set("notes", e.target.value)} />
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
          Cancel
        </button>
        <button type="submit" disabled={loading} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
          {loading ? "Saving..." : initial?.id ? "Update" : "Add Component"}
        </button>
      </div>
    </form>
  );
}
