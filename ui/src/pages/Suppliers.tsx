import { useSuppliers } from "../hooks/useSuppliers.ts";
import { Truck, ExternalLink, Clock } from "lucide-react";

export default function Suppliers() {
  const { data: suppliers, isLoading } = useSuppliers();

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">Suppliers</h1>

      {isLoading ? (
        <p className="text-gray-400">Loading...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {suppliers?.map((s) => (
            <div key={s.id} className="bg-white rounded-lg border p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Truck className="w-4 h-4 text-gray-400" />
                  <h3 className="font-semibold">{s.name}</h3>
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    s.api_type === "api"
                      ? "bg-green-100 text-green-700"
                      : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {s.api_type}
                </span>
              </div>

              {s.website && (
                <a
                  href={s.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-indigo-600 hover:underline flex items-center gap-1 mb-2"
                >
                  <ExternalLink className="w-3 h-3" />
                  {new URL(s.website).hostname}
                </a>
              )}

              <div className="flex items-center gap-2 text-xs text-gray-500 mt-2">
                <Clock className="w-3 h-3" />
                {s.last_polled_at
                  ? `Last polled: ${new Date(s.last_polled_at).toLocaleString()}`
                  : "Never polled"}
              </div>

              <div className="flex items-center gap-2 mt-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    s.poll_enabled ? "bg-green-400" : "bg-gray-300"
                  }`}
                />
                <span className="text-xs text-gray-500">
                  {s.poll_enabled ? "Polling enabled" : "Polling disabled"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
