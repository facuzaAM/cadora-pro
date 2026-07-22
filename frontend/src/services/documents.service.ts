import { api } from "./api";
import type { Document } from "@/types";

export const documentsService = {
  upload: (projectId: string, file: File, token?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.upload<Document>(`/documents/${projectId}`, formData, token);
  },

  getByProject: (projectId: string, token?: string) =>
    api.get<Document[]>(`/documents/project/${projectId}`, token),
};
