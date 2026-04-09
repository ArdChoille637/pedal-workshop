import { useQuery } from "@tanstack/react-query";
import { api, DashboardData, DashboardSummary } from "../api.ts";

export function useBuildTiers() {
  return useQuery({
    queryKey: ["dashboard", "build-tiers"],
    queryFn: () => api.get<DashboardData>("/dashboard/build-tiers"),
  });
}

export function useSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => api.get<DashboardSummary>("/dashboard/summary"),
  });
}
