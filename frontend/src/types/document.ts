export type DocumentType = "pdf" | "png" | "jpg" | "jpeg" | "tiff";

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  file_type: DocumentType;
  file_size: number;
  storage_path: string;
  created_at: string;
}
