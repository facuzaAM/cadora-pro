export interface OcrTextElement {
  id: string;
  text: string;
  category: "measurement" | "room_name" | "scale" | "note" | "unknown";
  confidence: number;
  bbox: [number, number, number, number]; // x_min, y_min, x_max, y_max
  font_size: number | null;
  rotation: number;
}

export interface OcrResult {
  texts: OcrTextElement[];
  measurements: OcrTextElement[];
  room_names: OcrTextElement[];
  scales: OcrTextElement[];
  notes: OcrTextElement[];
  raw_text: string;
  page_count: number;
}

// ── Legacy DetectionResult (kept for the full detection pipeline) ──────────

export interface DetectionResult {
  id: string;
  document_id: string;
  status: string;
  walls: Wall[];
  doors: Door[];
  windows: Window[];
  rooms: Room[];
  texts: TextElement[];
  dimensions: Dimension[];
  created_at: string;
}

export interface Wall {
  id: string;
  start_point: [number, number];
  end_point: [number, number];
  thickness: number;
  confidence: number;
}

export interface Door {
  id: string;
  position: [number, number];
  width: number;
  angle: number;
  swing_direction: "left" | "right" | "both";
  confidence: number;
}

export type WindowType = "sliding" | "fixed" | "casement";
export type WindowOrientation = "horizontal" | "vertical";

export interface WindowArc {
  center_x: number;
  center_y: number;
  radius: number;
  start_angle: number;
  end_angle: number;
}

export interface Window {
  id: string;
  type: WindowType;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  orientation: WindowOrientation;
  wall_gap_x1: number;
  wall_gap_y1: number;
  wall_gap_x2: number;
  wall_gap_y2: number;
  glass_lines: number;
  arc: WindowArc | null;
  confidence: number;
}

export interface WindowDetectionResult {
  windows: Window[];
  image_width: number;
  image_height: number;
}

export interface Room {
  id: string;
  name: string;
  area: number;
  perimeter: number;
  vertices: [number, number][];
  confidence: number;
}

export interface TextElement {
  id: string;
  text: string;
  position: [number, number];
  font_size: number;
  rotation: number;
  confidence: number;
}

export interface Dimension {
  id: string;
  value: number;
  unit: string;
  start_point: [number, number];
  end_point: [number, number];
  confidence: number;
}
