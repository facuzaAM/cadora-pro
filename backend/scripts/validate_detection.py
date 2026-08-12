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
from typing import TypedDict

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
    type: str = "single"


@dataclass
class GTWindow:
    x: float
    y: float
    width: float
    horizontal: bool = True
    type: str = "sliding"


@dataclass
class Plan:
    name: str
    size: tuple[int, int]
    walls: list[GTWall] = field(default_factory=list)
    doors: list[GTDoor] = field(default_factory=list)
    windows: list[GTWindow] = field(default_factory=list)
    grid: bool = False
    double_line: bool = False
    labels: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    # Furniture (closed boxes/circles) that must NOT be detected as walls.
    furniture: list[tuple[int, int, int, int]] = field(default_factory=list)
    circles: list[tuple[int, int, int]] = field(default_factory=list)  # (cx, cy, r)

    STROKE_GAP = 4   # half-distance from wall centre to each stroke line
    STROKE_W = 2

    def _stroke_positions(self, wall: GTWall) -> list[tuple[int, int, int, int]]:
        """Return the (x1, y1, x2, y2) of the ink strokes that make a wall."""
        if wall.y1 == wall.y2:  # horizontal
            return [(int(wall.x1), int(wall.y1) - self.STROKE_GAP,
                     int(wall.x2), int(wall.y2) - self.STROKE_GAP),
                    (int(wall.x1), int(wall.y1) + self.STROKE_GAP,
                     int(wall.x2), int(wall.y2) + self.STROKE_GAP)]
        return [(int(wall.x1) - self.STROKE_GAP, int(wall.y1),
                 int(wall.x2) - self.STROKE_GAP, int(wall.y2)),
                (int(wall.x1) + self.STROKE_GAP, int(wall.y1),
                 int(wall.x2) + self.STROKE_GAP, int(wall.y2))]

    def render(self) -> np.ndarray:
        img = np.full((self.size[1], self.size[0], 3), 255, dtype=np.uint8)
        if self.grid:
            for gx in range(0, self.size[0], 50):
                cv2.line(img, (gx, 0), (gx, self.size[1]), (200, 200, 200), 1)
            for gy in range(0, self.size[1], 50):
                cv2.line(img, (0, gy), (self.size[0], gy), (200, 200, 200), 1)
        for wall in self.walls:
            if self.double_line:
                for x1, y1, x2, y2 in self._stroke_positions(wall):
                    cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), self.STROKE_W)
            else:
                cv2.line(img, (int(wall.x1), int(wall.y1)),
                         (int(wall.x2), int(wall.y2)), (0, 0, 0), 4)
        for win in self.windows:
            self._draw_window(img, win)
        for d in self.doors:
            self._draw_door(img, d)
        for fx1, fy1, fx2, fy2 in self.furniture:
            cv2.rectangle(img, (int(fx1), int(fy1)),
                          (int(fx2), int(fy2)), (0, 0, 0), 3)
        for cx, cy, r in self.circles:
            cv2.circle(img, (int(cx), int(cy)), int(r), (0, 0, 0), 3)
        for text, (tx, ty), scale in self.labels:
            cv2.putText(
                img, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (0, 0, 0), 2, cv2.LINE_AA,
            )
        return img

    def _erase_strokes(self, img: np.ndarray, wall: GTWall,
                       a: int, b: int, horizontal: bool) -> None:
        """Erase both strokes of a double-line wall between positions a and b."""
        if horizontal:
            for off in (-self.STROKE_GAP, self.STROKE_GAP):
                cv2.line(img, (a, int(wall.y1) + off),
                         (b, int(wall.y2) + off), (255, 255, 255), self.STROKE_W + 2)
        else:
            for off in (-self.STROKE_GAP, self.STROKE_GAP):
                cv2.line(img, (int(wall.x1) + off, a),
                         (int(wall.x2) + off, b), (255, 255, 255), self.STROKE_W + 2)

    def _draw_window(self, img: np.ndarray, w: GTWindow) -> None:
        # The wall is broken by a frame (erased region); two thin glass lines
        # sit inside the gap, like a CAD symbol. On double-line walls both
        # strokes are broken and the glass runs between them.
        if w.horizontal:
            y = int(w.y)
            x1, x2 = int(w.x - w.width / 2), int(w.x + w.width / 2)
            if self.double_line:
                wall = GTWall(x1, y, x2, y)
                self._erase_strokes(img, wall, x1, x2, True)
                cv2.line(img, (x1, y - 2), (x2, y - 2), (0, 0, 0), 1)
                cv2.line(img, (x1, y + 2), (x2, y + 2), (0, 0, 0), 1)
            else:
                cv2.line(img, (x1, y), (x2, y), (255, 255, 255), 8)
                cv2.line(img, (x1, y - 2), (x2, y - 2), (0, 0, 0), 1)
                cv2.line(img, (x1, y + 2), (x2, y + 2), (0, 0, 0), 1)
        else:
            x = int(w.x)
            y1, y2 = int(w.y - w.width / 2), int(w.y + w.width / 2)
            if self.double_line:
                wall = GTWall(x, y1, x, y2)
                self._erase_strokes(img, wall, y1, y2, False)
                cv2.line(img, (x - 2, y1), (x - 2, y2), (0, 0, 0), 1)
                cv2.line(img, (x + 2, y1), (x + 2, y2), (0, 0, 0), 1)
            else:
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
            if self.double_line:
                wall = GTWall(x, top, x, int(d.y + half))
                self._erase_strokes(img, wall, top, int(d.y + half), False)
            else:
                cv2.line(img, (x, top), (x, int(d.y + half)), (255, 255, 255), 6)
            cv2.line(img, (x, top), (x + r, top), (0, 0, 0), 4)
            cv2.ellipse(img, (x, top), (r, r), 0, 180, 270, (0, 0, 0), 2)
        else:
            # Door in a horizontal wall: leaf hinged at the left end.
            y = int(d.y)
            left = int(d.x - half)
            if self.double_line:
                wall = GTWall(left, y, int(d.x + half), y)
                self._erase_strokes(img, wall, left, int(d.x + half), True)
            else:
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
        Plan(
            name="double_walls",
            size=(s, s),
            double_line=True,
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
                GTDoor(x=720, y=600, width=70),
            ],
            windows=[
                GTWindow(x=500, y=760, width=90, horizontal=False),
                GTWindow(x=350, y=600, width=90, horizontal=True),
            ],
        ),
        Plan(
            name="furniture",
            size=(s, s),
            walls=[
                GTWall(200, 200, 1000, 200),   # top
                GTWall(200, 1000, 1000, 1000), # bottom
                GTWall(200, 200, 200, 1000),   # left
                GTWall(1000, 200, 1000, 1000), # right
            ],
            furniture=[
                # bed (outer box + inner pillow lines)
                (300, 650, 560, 900),
                (320, 660, 400, 890),
            ],
            circles=[
                # round table
                (520, 430, 90),
            ],
        ),
        Plan(
            name="text_annotations",
            size=(s, s),
            walls=[
                GTWall(200, 200, 1000, 200),
                GTWall(200, 1000, 1000, 1000),
                GTWall(200, 200, 200, 1000),
                GTWall(1000, 200, 1000, 1000),
            ],
            labels=[
                ("COCINA", (350, 450), 1.0),
                ("DORMITORIO", (620, 700), 0.9),
                ("SALON", (400, 850), 1.0),
                ("AREA 120 m2", (260, 920), 0.8),
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


def _feature_box_iou(
    det_x: float, det_y: float, det_w: float,
    gt_x: float, gt_y: float, gt_w: float, gt_h: float,
) -> float:
    """IoU of two axis-aligned gap boxes (position + extent accuracy)."""
    gt_h = det_h = gt_h or 0.4 * gt_w
    ix = min(det_x + det_w / 2, gt_x + gt_w / 2) - max(det_x - det_w / 2, gt_x - gt_w / 2)
    iy = min(det_y + det_h / 2, gt_y + gt_h / 2) - max(det_y - det_h / 2, gt_y - gt_h / 2)
    inter = max(0.0, ix) * max(0.0, iy)
    det_area, gt_area = max(1e-6, det_w * det_h), max(1e-6, gt_w * gt_h)
    union = det_area + gt_area - inter
    return inter / union if union > 0 else 0.0


def _door_iou(det: Door, gt: GTDoor) -> float:
    return _feature_box_iou(det.x, det.y, det.width, gt.x, gt.y, gt.width, gt.width)


def _window_iou(det: Window, gt: GTWindow) -> float:
    return _feature_box_iou(det.x, det.y, det.width, gt.x, gt.y, gt.width, gt.width * 0.4)


def _report(name: str, tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print(f"  {name:<14} TP={tp:<3} FP={fp:<3} FN={fn:<3} "
          f"precision={precision:.2f} recall={recall:.2f} F1={f1:.2f}")
    return precision, recall


def _wall_iou(plan: Plan, grouped_lines: list[LineSegment]) -> float:
    """Pixel-level IoU between GT walls and detected walls (thickened masks).

    This measure is stricter than centre-of-line matching: it rewards how much
    of the true wall ink is covered by detected strokes and penalises walls
    that are displaced or that cover empty space.
    """
    h, w = plan.size[1], plan.size[0]
    gt = np.zeros((h, w), dtype=np.uint8)
    det = np.zeros((h, w), dtype=np.uint8)
    lw = 6  # thickness for tolerant matching
    for wall in plan.walls:
        cv2.line(gt, (int(wall.x1), int(wall.y1)),
                 (int(wall.x2), int(wall.y2)), 255, lw)
    for d in grouped_lines:
        cv2.line(det, (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2)), 255, lw)
    inter = int(np.logical_and(gt, det).sum())
    union = int(np.logical_or(gt, det).sum())
    if union == 0:
        return 1.0 if not (gt.any() or det.any()) else 0.0
    return inter / union


class Metrics(TypedDict):
    walls: tuple[float, float]
    doors: tuple[float, float]
    windows: tuple[float, float]
    walls_iou: float
    feature_iou: float
    type_accuracy: float | None


def validate_plan(plan: Plan, service: DetectionService) -> Metrics:
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
    walls_iou = _wall_iou(plan, line_result.grouped_lines)
    print(f"  walls IoU (pixel) = {walls_iou:.3f}")

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

    # Feature IoU (position + extent) and type accuracy across matched features.
    feature_ious: list[float] = []
    type_ok = matched_types = 0
    for dgt in plan.doors:
        d_mdet = [x for x in doors.doors if _door_match(x, dgt)]
        if d_mdet:
            feature_ious.append(max(_door_iou(x, dgt) for x in d_mdet))
            matched_types += 1
            if d_mdet[0].type.value == dgt.type:
                type_ok += 1
    for wgt in plan.windows:
        w_mdet = [x for x in windows.windows if _window_match(x, wgt)]
        if w_mdet:
            feature_ious.append(max(_window_iou(x, wgt) for x in w_mdet))
            matched_types += 1
            if w_mdet[0].type.value == wgt.type:
                type_ok += 1
    feature_iou = (sum(feature_ious) / len(feature_ious)) if feature_ious else 0.0
    type_accuracy = (type_ok / matched_types) if matched_types else None
    if feature_ious:
        print(f"  feature IoU = {feature_iou:.3f}    type accuracy = "
              f"{(type_accuracy if type_accuracy is not None else 0.0):.2f}")

    return {
        "walls": (w_prec, w_rec),
        "doors": (d_prec, d_rec),
        "windows": (win_prec, win_rec),
        "walls_iou": walls_iou,
        "feature_iou": feature_iou,
        "type_accuracy": type_accuracy,
    }


def main() -> None:
    service = DetectionService()
    print("=" * 64)
    for plan in build_plans():
        validate_plan(plan, service)
        print("-" * 64)


if __name__ == "__main__":
    main()
