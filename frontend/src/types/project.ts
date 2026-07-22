export type ProjectStatus =
  | "created"
  | "document_uploaded"
  | "processing"
  | "detection_completed"
  | "cad_generated"
  | "error";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  document_count: number;
  created_at: string;
  updated_at: string;
}
