import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Project, BOMItem } from "../api.ts";

export function useProjects(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return useQuery({
    queryKey: ["projects", params],
    queryFn: () => api.get<Project[]>(`/projects${qs}`),
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: () => api.get<Project>(`/projects/${id}`),
    enabled: id > 0,
  });
}

export function useBOMItems(projectId: number) {
  return useQuery({
    queryKey: ["projects", projectId, "bom"],
    queryFn: () => api.get<BOMItem[]>(`/projects/${projectId}/bom`),
    enabled: projectId > 0,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post<Project>("/projects", data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.put<Project>(`/projects/${id}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects", vars.id] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del(`/projects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useAddBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: number; data: Record<string, unknown> }) =>
      api.post<BOMItem>(`/projects/${projectId}/bom`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId, "bom"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, itemId, data }: { projectId: number; itemId: number; data: Record<string, unknown> }) =>
      api.put<BOMItem>(`/projects/${projectId}/bom/${itemId}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId, "bom"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteBOMItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, itemId }: { projectId: number; itemId: number }) =>
      api.del(`/projects/${projectId}/bom/${itemId}`),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["projects", vars.projectId, "bom"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
