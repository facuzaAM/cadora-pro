import { api } from "./api";

export const cadService = {
  generate: (projectId: string, token?: string) =>
    api.post<{ filename: string; file_size: number }>(
      `/cad/generate/${projectId}`,
      { format: "dxf" },
      token,
    ),

  downloadUrl: (projectId: string) =>
    `${api.getBaseUrl()}/cad/download/${projectId}`,

  getByProject: (projectId: string, token?: string) =>
    api.get(`/cad/project/${projectId}`, token),
};
