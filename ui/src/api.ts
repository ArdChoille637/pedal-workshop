const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || body.message || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};

// --- Types ---

export interface Component {
  id: number;
  category: string;
  subcategory: string | null;
  value: string;
  value_numeric: number | null;
  value_unit: string | null;
  package: string | null;
  description: string | null;
  manufacturer: string | null;
  mpn: string | null;
  quantity: number;
  min_quantity: number;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  effect_type: string | null;
  status: string;
  description: string | null;
  notes: string | null;
  schematic_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface BOMItem {
  id: number;
  project_id: number;
  component_id: number | null;
  reference: string | null;
  category: string;
  value: string;
  quantity: number;
  notes: string | null;
  is_optional: number;
  created_at: string;
}

export interface Build {
  id: number;
  project_id: number;
  name: string | null;
  status: string;
  quantity: number;
  started_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MissingPart {
  bom_item_id: number;
  reference: string | null;
  category: string;
  value: string;
  shortfall: number;
  cheapest_source: {
    supplier: string;
    price: number | null;
    in_stock: boolean | null;
  } | null;
}

export interface ProjectBuildStatus {
  project_id: number;
  project_name: string;
  effect_type: string | null;
  status: string;
  bom_count: number;
  missing_count: number;
  missing_parts: MissingPart[];
  estimated_cost: number | null;
}

export interface DashboardData {
  ready: ProjectBuildStatus[];
  arna_1_3: ProjectBuildStatus[];
  arna_4_plus: ProjectBuildStatus[];
}

export interface DashboardSummary {
  total_components: number;
  total_unique_parts: number;
  total_projects: number;
  active_builds: number;
  low_stock_count: number;
  ready_to_build: number;
  arna_1_3: number;
  arna_4_plus: number;
}

export interface Supplier {
  id: number;
  name: string;
  slug: string;
  website: string | null;
  api_type: string;
  poll_enabled: number;
  poll_interval: number;
  last_polled_at: string | null;
  created_at: string;
}
