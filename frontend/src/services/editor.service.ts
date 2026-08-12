import { api } from "./api";
import type { EditorDetection, EditorElements } from "@/types/editor";

export const editorService = {
  runDetection: (projectId: string, token?: string) =>
    api.post<{ status: string }>(`/projects/${projectId}/detection/run`, {}, token),

  getDetection: (projectId: string, token?: string) =>
    api.get<EditorDetection>(`/projects/${projectId}/detection`, token),

  saveElements: (projectId: string, elements: EditorElements, token?: string) =>
    api.put<{ ok: boolean }>(`/projects/${projectId}/elements`, elements, token),

  getElements: (projectId: string, token?: string) =>
    api.get<EditorElements | null>(`/projects/${projectId}/elements`, token),

  previewUrl: (projectId: string) => {
    // Same-origin image; the HttpOnly access cookie authenticates it, so we
    // never put the token in the URL (avoids leaking it via Referer/logs).
    return `${api.getBaseUrl()}/projects/${projectId}/preview/image`;
  },
};
