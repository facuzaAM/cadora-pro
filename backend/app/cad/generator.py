from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.math import Vec2

from app.detection.schemas import (
    DoorDetectionResult,
    LineDetectionResult,
    LineCategory,
    WindowDetectionResult,
    WindowType,
)
from app.ocr.schemas import OcrResult

# ── Layer configuration ──────────────────────────────────────────────────────
# Each layer: (name, ACI color, lineweight in 1/100 mm, linetype)
# Colors: 1=Red, 3=Green, 5=Blue, 6=Magenta, 7=White/Black, 8=Dark Gray
# Lineweight values are in hundredths of mm (35 = 0.35mm, 25 = 0.25mm, etc.)
LAYER_WALLS = ("Muros", 7, 35, "CONTINUOUS")
LAYER_DOORS = ("Puertas", 5, 25, "CONTINUOUS")
LAYER_WINDOWS = ("Ventanas", 3, 25, "CONTINUOUS")
LAYER_TEXTS = ("Textos", 6, 18, "CONTINUOUS")
LAYER_DIMENSIONS = ("Cotas", 1, 18, "CONTINUOUS")
LAYER_GRID = ("Cuadricula", 8, 13, "DOT")

LAYERS = [
    LAYER_WALLS,
    LAYER_DOORS,
    LAYER_WINDOWS,
    LAYER_TEXTS,
    LAYER_DIMENSIONS,
    LAYER_GRID,
]


class CadGenerator:
    """Generates a DXF file from detection results.

    Each element is placed on its corresponding layer with:
      - ACI color  (editable via AutoCAD PROPERTIES palette)
      - Lineweight (editable via AutoCAD PROPERTIES palette / LWDisplay)
      - Linetype   (editable via AutoCAD PROPERTIES palette)

    Layers are created with standard architectural conventions so they
    can be toggled, frozen, locked, or assigned plot styles in AutoCAD.
    """

    def __init__(self):
        self.doc = ezdxf.new("R2010")
        self.msp = self.doc.modelspace()

    def generate(
        self,
        lines_result: LineDetectionResult,
        doors_result: DoorDetectionResult,
        windows_result: WindowDetectionResult,
        ocr_result: OcrResult,
        output_path: str | Path,
    ) -> Path:
        self._setup_layers()
        self._draw_grid(lines_result.image_width, lines_result.image_height)
        self._draw_walls(lines_result.grouped_lines)
        self._draw_doors(doors_result.doors)
        self._draw_windows(windows_result.windows)
        self._draw_texts(ocr_result.texts)
        self._draw_dimensions(ocr_result.measurements)
        return self._save(output_path)

    # ── Layer setup ──────────────────────────────────────────────────────────

    def _setup_layers(self) -> None:
        for name, color, lw, ltype in LAYERS:
            layer = self.doc.layers.add(name)
            layer.color = color
            layer.dxf.lineweight = lw
            if ltype != "CONTINUOUS":
                try:
                    layer.linetype = ltype
                except Exception:
                    pass

    # ── Grid (reference rectangle) ───────────────────────────────────────────

    def _draw_grid(self, w: int, h: int) -> None:
        self.msp.add_line((0, 0), (w, 0), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((w, 0), (w, h), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((w, h), (0, h), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((0, h), (0, 0), dxfattribs={"layer": "Cuadricula"})

    # ── Walls ────────────────────────────────────────────────────────────────

    def _draw_walls(self, lines: list) -> None:
        for line in lines:
            if line.category not in (LineCategory.HORIZONTAL, LineCategory.VERTICAL):
                continue
            self.msp.add_line(
                (line.x1, line.y1),
                (line.x2, line.y2),
                dxfattribs={"layer": "Muros"},
            )

    # ── Doors ────────────────────────────────────────────────────────────────

    def _draw_doors(self, doors: list) -> None:
        for door in doors:
            self._draw_door_gap(door)
            self._draw_door_leaf(door)
            if door.arc is not None:
                self._draw_door_arc(door)

    def _draw_door_gap(self, door) -> None:
        gap_x1 = door.wall_gap_x1
        gap_y1 = door.wall_gap_y1
        gap_x2 = door.wall_gap_x2
        gap_y2 = door.wall_gap_y2
        self.msp.add_line(
            (gap_x1, gap_y1),
            (gap_x2, gap_y2),
            dxfattribs={"layer": "Puertas"},
        )

    def _draw_door_leaf(self, door) -> None:
        self.msp.add_line(
            (door.hinge_x, door.hinge_y),
            (door.leaf_x1, door.leaf_y1),
            dxfattribs={"layer": "Puertas"},
        )

    def _draw_door_arc(self, door) -> None:
        if door.arc is None:
            return
        cx, cy = door.arc.center_x, door.arc.center_y
        r = door.arc.radius
        sa = math.radians(door.arc.start_angle)
        ea = math.radians(door.arc.end_angle)

        pts = []
        steps = max(16, int(abs(ea - sa) / math.radians(5)))
        for i in range(steps + 1):
            t = sa + (ea - sa) * i / steps
            pts.append(Vec2(cx + r * math.cos(t), cy + r * math.sin(t)))

        if len(pts) >= 2:
            self.msp.add_polyline3d(
                pts,
                dxfattribs={"layer": "Puertas"},
            )

    # ── Windows ──────────────────────────────────────────────────────────────

    def _draw_windows(self, windows: list) -> None:
        for win in windows:
            if win.orientation.value == "horizontal":
                self._draw_horizontal_window(win)
            else:
                self._draw_vertical_window(win)

    def _draw_horizontal_window(self, win) -> None:
        y = win.wall_gap_y1
        x1 = win.wall_gap_x1
        x2 = win.wall_gap_x2
        half_h = win.height / 2.0 if win.height > 0 else 3.0

        top_y = y - half_h
        bot_y = y + half_h

        self.msp.add_line(
            (x1, top_y), (x2, top_y),
            dxfattribs={"layer": "Ventanas"},
        )
        self.msp.add_line(
            (x1, bot_y), (x2, bot_y),
            dxfattribs={"layer": "Ventanas"},
        )

        if win.type == WindowType.SLIDING:
            mid = (top_y + bot_y) / 2.0
            self.msp.add_line(
                (x1, mid), (x2, mid),
                dxfattribs={"layer": "Ventanas"},
            )

            third1 = top_y + (bot_y - top_y) / 3.0
            third2 = top_y + 2.0 * (bot_y - top_y) / 3.0
            self.msp.add_line(
                (x1, third1), (x2, third1),
                dxfattribs={"layer": "Ventanas"},
            )
            self.msp.add_line(
                (x1, third2), (x2, third2),
                dxfattribs={"layer": "Ventanas"},
            )

        if win.type == WindowType.CASEMENT and win.arc is not None:
            self.msp.add_line(
                (x1, top_y), (x1, bot_y),
                dxfattribs={"layer": "Ventanas"},
            )
            a = win.arc
            cx, cy = a.center_x, a.center_y
            r = a.radius
            sa = math.radians(a.start_angle)
            ea = math.radians(a.end_angle)
            pts = []
            steps = max(12, int(abs(ea - sa) / math.radians(5)))
            for i in range(steps + 1):
                t = sa + (ea - sa) * i / steps
                pts.append(Vec2(cx + r * math.cos(t), cy + r * math.sin(t)))
            if len(pts) >= 2:
                self.msp.add_polyline3d(
                    pts,
                    dxfattribs={"layer": "Ventanas"},
                )

    def _draw_vertical_window(self, win) -> None:
        x = win.wall_gap_x1
        y1 = win.wall_gap_y1
        y2 = win.wall_gap_y2
        half_w = win.height / 2.0 if win.height > 0 else 3.0

        left_x = x - half_w
        right_x = x + half_w

        self.msp.add_line(
            (left_x, y1), (left_x, y2),
            dxfattribs={"layer": "Ventanas"},
        )
        self.msp.add_line(
            (right_x, y1), (right_x, y2),
            dxfattribs={"layer": "Ventanas"},
        )

        if win.type == WindowType.SLIDING:
            mid = (left_x + right_x) / 2.0
            self.msp.add_line(
                (mid, y1), (mid, y2),
                dxfattribs={"layer": "Ventanas"},
            )
            third1 = left_x + (right_x - left_x) / 3.0
            third2 = left_x + 2.0 * (right_x - left_x) / 3.0
            self.msp.add_line(
                (third1, y1), (third1, y2),
                dxfattribs={"layer": "Ventanas"},
            )
            self.msp.add_line(
                (third2, y1), (third2, y2),
                dxfattribs={"layer": "Ventanas"},
            )

        if win.type == WindowType.CASEMENT and win.arc is not None:
            self.msp.add_line(
                (left_x, y1), (right_x, y1),
                dxfattribs={"layer": "Ventanas"},
            )
            a = win.arc
            cx, cy = a.center_x, a.center_y
            r = a.radius
            sa = math.radians(a.start_angle)
            ea = math.radians(a.end_angle)
            pts = []
            steps = max(12, int(abs(ea - sa) / math.radians(5)))
            for i in range(steps + 1):
                t = sa + (ea - sa) * i / steps
                pts.append(Vec2(cx + r * math.cos(t), cy + r * math.sin(t)))
            if len(pts) >= 2:
                self.msp.add_polyline3d(
                    pts,
                    dxfattribs={"layer": "Ventanas"},
                )

    # ── Texts ────────────────────────────────────────────────────────────────

    def _draw_texts(self, texts: list) -> None:
        for t in texts:
            x_min, y_min, x_max, y_max = t.bbox
            cx = (x_min + x_max) / 2.0
            cy = (y_min + y_max) / 2.0
            height = max(y_max - y_min, 2.5)

            self.msp.add_mtext(
                t.text,
                dxfattribs={
                    "layer": "Textos",
                    "char_height": height,
                },
            ).set_location(
                (cx, cy),
                attachment_point=5,
            )

    # ── Dimensions / Measurements ────────────────────────────────────────────

    def _draw_dimensions(self, measurements: list) -> None:
        for m in measurements:
            x_min, y_min, x_max, y_max = m.bbox
            cx = (x_min + x_max) / 2.0
            cy = (y_min + y_max) / 2.0
            height = max(y_max - y_min, 2.5)

            self.msp.add_mtext(
                m.text,
                dxfattribs={
                    "layer": "Cotas",
                    "char_height": height,
                },
            ).set_location(
                (cx, cy),
                attachment_point=5,
            )

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.saveas(str(path))
        return path
