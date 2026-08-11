"""Validation harness for the detection pipeline.

Renders synthetic floor plans with known ground truth (walls, doors,
windows), runs the full detection pipeline, and reports precision/recall.

Usage:
    python -m scripts.validate_detection
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.detection.schemas import Door, LineSegment, Window  # noqa: E402
from app.detection.service import DetectionService  # noqa: E402

# ── ground truth ──────────────────────────────────────────────────────

@dataclass
class GTWall:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class GTDoor:
    x: float
    y: float
    width: float
    vertical_wall: bool = False


@dataclass
class GTWindow:
    x: float
    y: float
    width: float
    horizontal: bool = True


@dataclass
class Plan:
    name: str
    size: tuple[int, int]
    walls: list[GTWall] = field(default_factory=list)
    doors: list[GTDoor] = field(default_factory=list)
    windows: list[GTWindow] = field(default_factory=list)
    grid: bool = False

    def render(self) -> np.ndarray:
        img = np.full((self.size[1], self.size[0], 3), 255, dtype=np.uint8)
        if self.grid:
            for gx in range(0, self.size[0], 50):
                cv2.line(img, (gx, 0), (gx, self.size[1]), (200, 200, 200), 1)
            for gy in range(0, self.size[1], 50):
                cv2.line(img, (0, gy), (self.size[0], gy), (200, 200, 200), 1)
        for wall in self.walls:
            cv2.line(img, (int(wall.x1), int(wall.y1)),
                     (int(wall.x2), int(wall.y2)), (0, 0, 0), 4)
        for win in self.windows:
            self._draw_window(img, win)
        for d in self.doors:
            self._draw_door(img, d)
        return img

    def _draw_window(self, img: np.ndarray, w: GTWindow) -> None:
        # The wall is broken by a frame (erased region); two thin glass lines
        # sit at the frame's inner edges, a few px apart, like a CAD symbol.
        if w.horizontal:
            y = int(w.y)
            x1, x2 = int(w.x - w.width / 2), int(w.x + w.width / 2)
            cv2.line(img, (x1, y), (x2, y), (255, 255, 255), 8)
            cv2.line(img, (x1, y - 2), (x2, y - 2), (0, 0, 0), 1)
            cv2.line(img, (x1, y + 2), (x2, y + 2), (0, 0, 0), 1)
        else:
            x = int(w.x)
            y1, y2 = int(w.y - w.width / 2), int(w.y + w.width / 2)
            cv2.line(img, (x, y1), (x, y2), (255, 255, 255), 8)
            cv2.line(img, (x - 2, y1), (x - 2, y2), (0, 0, 0), 1)
            cv2.line(img, (x + 2, y1), (x + 2, y2), (0, 0, 0), 1)

    def _draw_door(self, img: np.ndarray, d: GTDoor) -> None:
        half = d.width / 2
        r = int(d.width * 0.5)
        if d.vertical_wall:
            # Door in a vertical wall: gap erased, leaf hinged at the top end,
            # swing arc drawn in the quadrant the detector scans (180-270).
            x = int(d.x)
            top = int(d.y - half)
            cv2.line(img, (x, top), (x, int(d.y + half)), (255, 255, 255), 6)
            cv2.line(img, (x, top), (x + r, top), (0, 0, 0), 4)
            cv2.ellipse(img, (x, top), (r, r), 0, 180, 270, (0, 0, 0), 2)
        else:
            # Door in a horizontal wall: leaf hinged at the left end.
            y = int(d.y)
            left = int(d.x - half)
            cv2.line(img, (left, y), (int(d.x + half), y), (255, 255, 255), 6)
            cv2.line(img, (left, y), (left, y + r), (0, 0, 0), 4)
            cv2.ellipse(img, (left, y), (r, r), 0, 90, 180, (0, 0, 0), 2)


# ── plans ─────────────────────────────────────────────────────────────

def build_plans() -> list[Plan]:
    s = 1200
    return [
        Plan(
            name="outer_shell",
            size=(s, s),
            walls=[
                GTWall(200, 200, 1000, 200),   # top
                GTWall(200, 1000, 1000, 1000), # bottom
                GTWall(200, 200, 200, 1000),   # left
                GTWall(1000, 200, 1000, 1000), # right
            ],
        ),
        Plan(
            name="interior_walls",
            size=(s, s),
            walls=[
                GTWall(200, 200, 1000, 200),
                GTWall(200, 1000, 1000, 1000),
                GTWall(200, 200, 200, 1000),
                GTWall(1000, 200, 1000, 1000),
                GTWall(500, 200, 500, 1000),   # interior vertical
                GTWall(200, 600, 1000, 600),   # interior horizontal
            ],
        ),
        Plan(
            name="doors_windows",
            size=(s, s),
            walls=[
                GTWall(200, 200, 1000, 200),
                GTWall(200, 1000, 1000, 1000),
                GTWall(200, 200, 200, 1000),
                GTWall(1000, 200, 1000, 1000),
                GTWall(500, 200, 500, 1000),
                GTWall(200, 600, 1000, 600),
            ],
            doors=[
                # gap in the interior vertical wall x=500
                GTDoor(x=500, y=320, width=70, vertical_wall=True),
                # gap in the interior horizontal wall y=600
                GTDoor(x=720, y=600, width=70),
            ],
            windows=[
                # gap in interior vertical wall x=500
                GTWindow(x=500, y=760, width=90, horizontal=False),
                # gap in interior horizontal wall y=600
                GTWindow(x=350, y=600, width=90, horizontal=True),
            ],
        ),
        Plan(
            name="grid_background",
            size=(s, s),
            grid=True,
            walls=[
                GTWall(200, 200, 1000, 200),
                GTWall(200, 1000, 1000, 1000),
                GTWall(200, 200, 200, 1000),
                GTWall(1000, 200, 1000, 1000),
                GTWall(500, 200, 500, 1000),
                GTWall(200, 600, 1000, 600),
            ],
            doors=[
                GTDoor(x=500, y=320, width=70, vertical_wall=True),
            ],
            windows=[
                GTWindow(x=350, y=600, width=90, horizontal=True),
            ],
        ),
    ]


# ── matching ──────────────────────────────────────────────────────────

def _seg_length(x1, y1, x2, y2) -> float:
    return float(np.hypot(x2 - x1, y2 - y1))


def _wall_match(det: LineSegment, gt: GTWall) -> bool:
    """Detected segment overlaps a GT wall line (axis aligned, close)."""
    tol = 12
    if det.category.value == "horizontal":
        if abs((det.y1 + det.y2) / 2 - gt.y1) > tol or abs(gt.y1 - gt.y2) > 1:
            return False
        det_min, det_max = min(det.x1, det.x2), max(det.x1, det.x2)
        gt_min, gt_max = min(gt.x1, gt.x2), max(gt.x1, gt.x2)
        overlap = min(det_max, gt_max) - max(det_min, gt_min)
        return overlap > 0.5 * min(det_max - det_min, gt_max - gt_min)
    if det.category.value == "vertical":
        if abs((det.x1 + det.x2) / 2 - gt.x1) > tol or abs(gt.x1 - gt.x2) > 1:
            return False
        det_min, det_max = min(det.y1, det.y2), max(det.y1, det.y2)
        gt_min, gt_max = min(gt.y1, gt.y2), max(gt.y1, gt.y2)
        overlap = min(det_max, gt_max) - max(det_min, gt_min)
        return overlap > 0.5 * min(det_max - det_min, gt_max - gt_min)
    return False


def _door_match(det: Door, gt: GTDoor) -> bool:
    return abs(det.x - gt.x) <= 40 and abs(det.y - gt.y) <= 40


def _window_match(det: Window, gt: GTWindow) -> bool:
    return abs(det.x - gt.x) <= 40 and abs(det.y - gt.y) <= 40


def _report(name: str, tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print(f"  {name:<14} TP={tp:<3} FP={fp:<3} FN={fn:<3} "
          f"precision={precision:.2f} recall={recall:.2f} F1={f1:.2f}")
    return precision, recall


def validate_plan(plan: Plan, service: DetectionService) -> dict[str, tuple[float, float]]:
    img = plan.render()
    line_result, doors, windows = service._process_image_all(img)

    # walls recall: each GT wall matched by a detected grouped segment
    walls_tp = 0
    for gt in plan.walls:
        if any(_wall_match(d, gt) for d in line_result.grouped_lines):
            walls_tp += 1
    walls_fn = len(plan.walls) - walls_tp

    shortest = min(_seg_length(w.x1, w.y1, w.x2, w.y2) for w in plan.walls) if plan.walls else 0.0
    walls_fp = sum(
        1 for d in line_result.grouped_lines
        if _seg_length(d.x1, d.y1, d.x2, d.y2) >= shortest * 0.5
        and not any(_wall_match(d, gt) for gt in plan.walls)
    )

    print(f"Plan: {plan.name} ({plan.size[0]}x{plan.size[1]})")
    print(f"  detected: {len(line_result.grouped_lines)} grouped lines, "
          f"{len(doors.doors)} doors, {len(windows.windows)} windows")
    w_prec, w_rec = _report("walls", walls_tp, walls_fp, walls_fn)

    d_prec, d_rec = 0.0, 0.0
    if plan.doors:
        d_tp = sum(1 for gt in plan.doors
                   if any(_door_match(d, gt) for d in doors.doors))
        d_fp = sum(1 for d in doors.doors
                   if not any(_door_match(d, gt) for gt in plan.doors))
        d_prec, d_rec = _report("doors", d_tp, d_fp, len(plan.doors) - d_tp)

    win_prec, win_rec = 0.0, 0.0
    if plan.windows:
        w_tp = sum(1 for gt in plan.windows
                   if any(_window_match(d, gt) for d in windows.windows))
        w_fp = sum(1 for d in windows.windows
                   if not any(_window_match(d, gt) for gt in plan.windows))
        win_prec, win_rec = _report("windows", w_tp, w_fp, len(plan.windows) - w_tp)

    return {"walls": (w_prec, w_rec), "doors": (d_prec, d_rec), "windows": (win_prec, win_rec)}


def main() -> None:
    service = DetectionService()
    print("=" * 64)
    for plan in build_plans():
        validate_plan(plan, service)
        print("-" * 64)


if __name__ == "__main__":
    main()
