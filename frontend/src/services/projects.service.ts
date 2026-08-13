import { api } from "./api";
import type { Project } from "@/types";

export const projectsService = {
  // The backend caps this at 100; asking explicitly stops the list being
  // silently truncated to the default 20 for users with many projects.
  list: (token?: string) => api.get<Project[]>("/projects", token, { limit: 100 }),
  getTotal: (token?: string) => api.get<{ total: number }>("/projects/total", token),

  getById: (id: string, token?: string) =>
    api.get<Project>(`/projects/${id}`, token),

  create: (data: { name: string; description?: string }, token?: string) =>
    api.post<Project>("/projects", data, token),

  delete: (id: string, token?: string) =>
    api.delete(`/projects/${id}`, token),
};
