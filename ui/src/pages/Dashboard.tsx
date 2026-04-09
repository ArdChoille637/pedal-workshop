import { useBuildTiers, useSummary } from "../hooks/useDashboard.ts";
import { ProjectBuildStatus } from "../api.ts";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Package,
  FolderKanban,
  Hammer,
  TrendingDown,
} from "lucide-react";

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white rounded-lg border p-4 flex items-center gap-4">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

function TierSection({
  title,
  badgeColor,
  projects,
  icon: Icon,
}: {
  title: string;
  badgeColor: string;
  projects: ProjectBuildStatus[];
  icon: React.ElementType;
}) {
  return (
    <div className="bg-white rounded-lg border">
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5" />
          <h2 className="font-semibold">{title}</h2>
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${badgeColor}`}>
          {projects.length} {projects.length === 1 ? "project" : "projects"}
        </span>
      </div>
      {projects.length === 0 ? (
        <p className="p-4 text-sm text-gray-400 italic">No projects in this tier</p>
      ) : (
        <div className="divide-y">
          {projects.map((p) => (
            <div key={p.project_id} className="p-4">
              <div className="flex items-center justify-between mb-1">
                <div>
                  <span className="font-medium">{p.project_name}</span>
                  {p.effect_type && (
                    <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      {p.effect_type}
                    </span>
                  )}
                </div>
                <span className="text-sm text-gray-500">{p.bom_count} parts</span>
              </div>
              {p.missing_count > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 mb-1">
                    Missing {p.missing_count} part{p.missing_count > 1 ? "s" : ""}
                    {p.estimated_cost != null && (
                      <span className="ml-1">
                        (est. ${p.estimated_cost.toFixed(2)})
                      </span>
                    )}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {p.missing_parts.map((mp) => (
                      <span
                        key={mp.bom_item_id}
                        className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded"
                        title={`${mp.reference || ""} ${mp.category} ${mp.value} x${mp.shortfall}${
                          mp.cheapest_source
                            ? ` - ${mp.cheapest_source.supplier} $${mp.cheapest_source.price}`
                            : ""
                        }`}
                      >
                        {mp.reference && `${mp.reference}: `}
                        {mp.value} x{mp.shortfall}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data: tiers, isLoading: tiersLoading } = useBuildTiers();
  const { data: summary, isLoading: summaryLoading } = useSummary();

  if (tiersLoading || summaryLoading) {
    return (
      <div className="p-8">
        <p className="text-gray-400">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Parts on Hand" value={summary.total_components} icon={Package} color="bg-blue-100 text-blue-600" />
          <StatCard label="Unique Parts" value={summary.total_unique_parts} icon={Package} color="bg-purple-100 text-purple-600" />
          <StatCard label="Projects" value={summary.total_projects} icon={FolderKanban} color="bg-indigo-100 text-indigo-600" />
          <StatCard label="Active Builds" value={summary.active_builds} icon={Hammer} color="bg-green-100 text-green-600" />
        </div>
      )}

      {/* Build tiers */}
      {tiers && (
        <div className="space-y-6">
          <TierSection
            title="Ready to Build"

            badgeColor="bg-green-100 text-green-700"
            projects={tiers.ready}
            icon={CheckCircle}
          />
          <TierSection
            title="ARNA 1-3 (Need 1-3 Parts)"
            badgeColor="bg-yellow-100 text-yellow-700"
            projects={tiers.arna_1_3}
            icon={AlertTriangle}
          />
          <TierSection
            title="ARNA 4+ (Need 4+ Parts)"
            badgeColor="bg-red-100 text-red-700"
            projects={tiers.arna_4_plus}
            icon={XCircle}
          />
        </div>
      )}

      {/* Low stock alert */}
      {summary && summary.low_stock_count > 0 && (
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <TrendingDown className="w-5 h-5 text-amber-600" />
          <p className="text-sm text-amber-800">
            <strong>{summary.low_stock_count}</strong> component{summary.low_stock_count > 1 ? "s" : ""} below minimum stock level
          </p>
        </div>
      )}
    </div>
  );
}
