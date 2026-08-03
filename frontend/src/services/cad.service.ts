import { api } from "./api";

export type CadFormat = "dxf" | "dwg";

export const cadService = {
  generate: (
    projectId: string,
    format: CadFormat = "dxf",
    token?: string,
    force = false,
  ) =>
    api.post<{ filename: string; file_size: number }>(
      `/cad/generate/${projectId}`,
      { format, force },
      token,
    ),

  downloadUrl: (projectId: string, format: CadFormat = "dxf") =>
    `${api.getBaseUrl()}/cad/download/${projectId}?format=${format}`,

};
