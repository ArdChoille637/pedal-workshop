import { useQuery } from "@tanstack/react-query";
import { api, Supplier } from "../api.ts";

export function useSuppliers() {
  return useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api.get<Supplier[]>("/suppliers"),
  });
}
