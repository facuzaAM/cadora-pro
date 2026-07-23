from __future__ import annotations

import contextlib
import logging
import math
import shutil
import subprocess
from pathlib import Path

import ezdxf

from app.detection.schemas import (
    DoorDetectionResult,
    LineCategory,
    LineDetectionResult,
    WindowDetectionResult,
    WindowType,
)
from app.ocr.scale import detect_scale_factor
from app.ocr.schemas import OcrResult

logger = logging.getLogger(__name__)

# ── Layer configuration ──────────────────────────────────────────────────────
# Each layer: (name, ACI color, lineweight in 1/100 mm, linetype)
# Colors: 1=Red, 3=Green, 5=Blue, 6=Magenta, 7=White/Black, 8=Dark Gray
LAYER_WALLS = ("Muros", 7, 35, "CONTINUOUS")
LAYER_DIAGONALS = ("Diagonales", 8, 25, "CONTINUOUS")
LAYER_DOORS = ("Puertas", 5, 25, "CONTINUOUS")
LAYER_WINDOWS = ("Ventanas", 3, 25, "CONTINUOUS")
LAYER_TEXTS = ("Textos", 6, 18, "CONTINUOUS")
LAYER_DIMENSIONS = ("Cotas", 1, 18, "CONTINUOUS")
LAYER_GRID = ("Cuadricula", 8, 13, "DOT")

LAYERS = [
    LAYER_WALLS,
    LAYER_DIAGONALS,
    LAYER_DOORS,
    LAYER_WINDOWS,
    LAYER_TEXTS,
    LAYER_DIMENSIONS,
    LAYER_GRID,
]


class CadGenerator:
    """Generates a DXF file from detection results.

    Features:
      - Automatic scale detection from OCR (pixels -> meters)
      - Proper DXF ARC entities (not polyline3d)
      - Diagonal lines on dedicated layer
      - Standard architectural layer conventions
    """

    def generate(
        self,
        lines_result: LineDetectionResult,
        doors_result: DoorDetectionResult,
        windows_result: WindowDetectionResult,
        ocr_result: OcrResult,
        output_path: str | Path,
    ) -> Path:
        self.doc = ezdxf.new("R2010")
        self.msp = self.doc.modelspace()

        scale_ppm = detect_scale_factor(ocr_result, lines_result.image_width)
        self.scale = scale_ppm if scale_ppm else 1.0
        self._setup_units()

        self._setup_layers()
        self._draw_grid(lines_result.image_width, lines_result.image_height)
        self._draw_walls(lines_result.grouped_lines)
        self._draw_doors(doors_result.doors)
        self._draw_windows(windows_result.windows)
        self._draw_texts(ocr_result.texts)
        self._draw_dimensions(ocr_result.measurements)
        return self._save(output_path)

    # ── Units & Scale ────────────────────────────────────────────────────────

    def _setup_units(self) -> None:
        self.doc.units = ezdxf.units.M
        if self.scale != 1.0:
            self.doc.header["$INSUNITS"] = 4

    def _s(self, value: float) -> float:
        return value / self.scale if self.scale != 1.0 else value

    # ── Layer setup ──────────────────────────────────────────────────────────

    def _setup_layers(self) -> None:
        for name, color, lw, ltype in LAYERS:
            layer = self.doc.layers.add(name)
            layer.color = color
            layer.dxf.lineweight = lw
            if ltype != "CONTINUOUS":
                with contextlib.suppress(Exception):
                    layer.linetype = ltype

    # ── Grid (reference rectangle) ───────────────────────────────────────────

    def _draw_grid(self, w: int, h: int) -> None:
        sw, sh = self._s(w), self._s(h)
        self.msp.add_line((0, 0), (sw, 0), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((sw, 0), (sw, sh), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((sw, sh), (0, sh), dxfattribs={"layer": "Cuadricula"})
        self.msp.add_line((0, sh), (0, 0), dxfattribs={"layer": "Cuadricula"})

    # ── Walls ────────────────────────────────────────────────────────────────

    def _draw_walls(self, lines: list) -> None:
        for line in lines:
            if line.category == LineCategory.DIAGONAL:
                self.msp.add_line(
                    (self._s(line.x1), self._s(line.y1)),
                    (self._s(line.x2), self._s(line.y2)),
                    dxfattribs={"layer": "Diagonales"},
                )
            elif line.category in (LineCategory.HORIZONTAL, LineCategory.VERTICAL):
                self.msp.add_line(
                    (self._s(line.x1), self._s(line.y1)),
                    (self._s(line.x2), self._s(line.y2)),
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
        self.msp.add_line(
            (self._s(door.wall_gap_x1), self._s(door.wall_gap_y1)),
            (self._s(door.wall_gap_x2), self._s(door.wall_gap_y2)),
            dxfattribs={"layer": "Puertas"},
        )

    def _draw_door_leaf(self, door) -> None:
        self.msp.add_line(
            (self._s(door.hinge_x), self._s(door.hinge_y)),
            (self._s(door.leaf_x1), self._s(door.leaf_y1)),
            dxfattribs={"layer": "Puertas"},
        )

    def _draw_door_arc(self, door) -> None:
        if door.arc is None:
            return
        cx = self._s(door.arc.center_x)
        cy = self._s(door.arc.center_y)
        r = self._s(door.arc.radius)
        sa = door.arc.start_angle
        ea = door.arc.end_angle

        if r < 0.01:
            return

        try:
            self.msp.add_arc(
                center=(cx, cy),
                radius=r,
                start_angle=sa,
                end_angle=ea,
                dxfattribs={"layer": "Puertas"},
            )
        except Exception:
            pts = []
            sa_rad = math.radians(sa)
            ea_rad = math.radians(ea)
            steps = max(16, int(abs(ea_rad - sa_rad) / math.radians(5)))
            for i in range(steps + 1):
                t = sa_rad + (ea_rad - sa_rad) * i / steps
                pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
            if len(pts) >= 2:
                self.msp.add_lwpolyline(
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
        y = self._s(win.wall_gap_y1)
        x1 = self._s(win.wall_gap_x1)
        x2 = self._s(win.wall_gap_x2)
        half_h = self._s(win.height / 2.0) if win.height > 0 else self._s(3.0)

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

        if win.type == WindowType.CASEMENT and win.arc is not None:
            self.msp.add_line(
                (x1, top_y), (x1, bot_y),
                dxfattribs={"layer": "Ventanas"},
            )
            a = win.arc
            cx = self._s(a.center_x)
            cy = self._s(a.center_y)
            r = self._s(a.radius)
            sa = a.start_angle
            ea = a.end_angle
            if r >= 0.01:
                try:
                    self.msp.add_arc(
                        center=(cx, cy), radius=r,
                        start_angle=sa, end_angle=ea,
                        dxfattribs={"layer": "Ventanas"},
                    )
                except Exception:
                    pts = []
                    sa_r = math.radians(sa)
                    ea_r = math.radians(ea)
                    steps = max(12, int(abs(ea_r - sa_r) / math.radians(5)))
                    for i in range(steps + 1):
                        t = sa_r + (ea_r - sa_r) * i / steps
                        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
                    if len(pts) >= 2:
                        self.msp.add_lwpolyline(
                            pts, dxfattribs={"layer": "Ventanas"},
                        )

    def _draw_vertical_window(self, win) -> None:
        x = self._s(win.wall_gap_x1)
        y1 = self._s(win.wall_gap_y1)
        y2 = self._s(win.wall_gap_y2)
        half_w = self._s(win.height / 2.0) if win.height > 0 else self._s(3.0)

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

        if win.type == WindowType.CASEMENT and win.arc is not None:
            self.msp.add_line(
                (left_x, y1), (right_x, y1),
                dxfattribs={"layer": "Ventanas"},
            )
            a = win.arc
            cx = self._s(a.center_x)
            cy = self._s(a.center_y)
            r = self._s(a.radius)
            sa = a.start_angle
            ea = a.end_angle
            if r >= 0.01:
                try:
                    self.msp.add_arc(
                        center=(cx, cy), radius=r,
                        start_angle=sa, end_angle=ea,
                        dxfattribs={"layer": "Ventanas"},
                    )
                except Exception:
                    pts = []
                    sa_r = math.radians(sa)
                    ea_r = math.radians(ea)
                    steps = max(12, int(abs(ea_r - sa_r) / math.radians(5)))
                    for i in range(steps + 1):
                        t = sa_r + (ea_r - sa_r) * i / steps
                        pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
                    if len(pts) >= 2:
                        self.msp.add_lwpolyline(
                            pts, dxfattribs={"layer": "Ventanas"},
                        )

    # ── Texts ────────────────────────────────────────────────────────────────

    def _draw_texts(self, texts: list) -> None:
        for t in texts:
            x_min, y_min, x_max, y_max = t.bbox
            cx = self._s((x_min + x_max) / 2.0)
            cy = self._s((y_min + y_max) / 2.0)
            height = self._s(max(y_max - y_min, 2.5))

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
            cx = self._s((x_min + x_max) / 2.0)
            cy = self._s((y_min + y_max) / 2.0)
            height = self._s(max(y_max - y_min, 2.5))

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


def convert_dxf_to_dwg(dxf_path: Path, dwg_path: Path) -> bool:
    """Convert a DXF file to DWG using dxf2dwg (libredwg).

    Returns True on success, False otherwise.
    """
    dxf2dwg = shutil.which("dxf2dwg")
    if dxf2dwg is None:
        logger.warning("dxf2dwg not found in PATH, DWG conversion unavailable")
        return False

    try:
        result = subprocess.run(
            [dxf2dwg, "-o", str(dwg_path), str(dxf_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("dxf2dwg failed: %s", result.stderr)
            return False
        return dwg_path.exists()
    except subprocess.TimeoutExpired:
        logger.error("dxf2dwg timed out")
        return False
    except FileNotFoundError:
        logger.error("dxf2dwg binary not found")
        return False
