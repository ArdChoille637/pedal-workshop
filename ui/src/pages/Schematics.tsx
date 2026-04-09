import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api.ts";
import { Search, FileImage } from "lucide-react";

interface SchematicItem {
  id: number;
  category_folder: string;
  file_name: string;
  file_path: string;
  file_type: string;
  effect_type: string | null;
}

export default function Schematics() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");

  const params = new URLSearchParams();
  if (search) params.set("q", search);
  if (category) params.set("category", category);
  params.set("limit", "200");

  const { data: schematics, isLoading } = useQuery({
    queryKey: ["schematics", search, category],
    queryFn: () => api.get<SchematicItem[]>(`/schematics?${params}`),
  });

  const { data: categories } = useQuery({
    queryKey: ["schematic-categories"],
    queryFn: () => api.get<string[]>("/schematics/categories"),
  });

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Schematic Library</h1>

      <div className="flex gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search schematics..."
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
          {categories?.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="bg-white rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Category</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Effect</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {schematics?.map((s) => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <a
                      href={`/api/schematics/${s.id}/file`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-indigo-600 hover:underline"
                    >
                      <FileImage className="w-4 h-4" />
                      {s.file_name}
                    </a>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{s.category_folder}</td>
                  <td className="px-4 py-2">
                    <span className="text-xs bg-gray-100 px-2 py-0.5 rounded uppercase">
                      {s.file_type}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-500">{s.effect_type || "-"}</td>
                </tr>
              ))}
              {schematics?.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    No schematics found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-gray-400 mt-4">
        {schematics?.length || 0} schematics shown
      </p>
    </div>
  );
}
