import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Component } from "../api.ts";

export function useComponents(params?: Record<string, string>) {
  const qs = params
    ? "?" + new URLSearchParams(params).toString()
    : "";
  return useQuery({
    queryKey: ["components", params],
    queryFn: () => api.get<Component[]>(`/components${qs}`),
  });
}

export function useComponent(id: number) {
  return useQuery({
    queryKey: ["components", id],
    queryFn: () => api.get<Component>(`/components/${id}`),
    enabled: id > 0,
  });
}

export function useCreateComponent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post<Component>("/components", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["components"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateComponent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.put<Component>(`/components/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["components"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteComponent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del(`/components/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["components"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useAdjustQuantity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, delta, reason }: { id: number; delta: number; reason?: string }) =>
      api.patch<Component>(`/components/${id}/quantity`, { delta, reason: reason || "adjustment" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["components"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
