export interface EditorWall {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface EditorDoor {
  id: string;
  type: "single" | "double" | "sliding";
  x: number;
  y: number;
  width: number;
  rotation: number;
  swing: "right" | "left";
}

export interface EditorWindow {
  id: string;
  type: "sliding" | "fixed" | "casement";
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
}

export interface EditorElements {
  walls: EditorWall[];
  doors: EditorDoor[];
  windows: EditorWindow[];
}

export interface EditorText {
  text: string;
  bbox: [number, number, number, number];
}

export interface EditorDetection extends EditorElements {
  status: "completed" | "processing" | "pending";
  ocr_texts: EditorText[];
  ocr_measurements: EditorText[];
  image_width: number;
  image_height: number;
}
