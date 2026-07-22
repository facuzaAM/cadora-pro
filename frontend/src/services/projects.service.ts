import { api } from "./api";
import type { Project } from "@/types";

export const projectsService = {
  list: (token?: string) => api.get<Project[]>("/projects", token),

  getById: (id: string, token?: string) =>
    api.get<Project>(`/projects/${id}`, token),

  create: (data: { name: string; description?: string }, token?: string) =>
    api.post<Project>("/projects", data, token),

  delete: (id: string, token?: string) =>
    api.post(`/projects/${id}/delete`, {}, token),
};
