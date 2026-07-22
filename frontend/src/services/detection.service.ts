import { api } from "./api";
import type { DetectionResult } from "@/types";

export const detectionService = {
  start: (documentId: string, token?: string) =>
    api.post<{ detection_id: string }>(
      `/detection/start`,
      { document_id: documentId },
      token,
    ),

  status: (detectionId: string, token?: string) =>
    api.get<{ status: string; progress: number }>(
      `/detection/${detectionId}/status`,
      token,
    ),

  result: (detectionId: string, token?: string) =>
    api.get<DetectionResult>(`/detection/${detectionId}/result`, token),
};
