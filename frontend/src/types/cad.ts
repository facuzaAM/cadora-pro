export type CadFormat = "dxf" | "dwg";

export interface CadFile {
  id: string;
  project_id: string;
  detection_id: string;
  format: CadFormat;
  storage_path: string;
  file_size: number;
  created_at: string;
}
