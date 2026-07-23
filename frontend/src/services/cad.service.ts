import { api } from "./api";

export type CadFormat = "dxf" | "dwg";

export const cadService = {
  generate: (projectId: string, format: CadFormat = "dxf", token?: string) =>
    api.post<{ filename: string; file_size: number }>(
      `/cad/generate/${projectId}`,
      { format },
      token,
    ),

  downloadUrl: (projectId: string, format: CadFormat = "dxf") =>
    `${api.getBaseUrl()}/cad/download/${projectId}?format=${format}`,

  getByProject: (projectId: string, token?: string) =>
    api.get(`/cad/project/${projectId}`, token),
};
