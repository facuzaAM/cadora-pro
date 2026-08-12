"""Evaluate the detection engine against a real, labeled dataset.

This is the harness for the market-differentiating measure: how precise the
engine really is on real floor plans (AI images, scans), not just synthetic
rectangles. The synthetic plans in `validate_detection` are a good smoke test,
but IoU on real data is what tells you whether the engine is world-class.

Ground-truth format (one JSON file per image, same basename, in a sibling or
`samples/` folder):

    {
      "image": "plano_a.png",
      "walls": [ {"x1":..., "y1":..., "x2":..., "y2":...} ],   # center lines px
      "doors": [ {"x":..., "y":..., "width":...} ],             # px, center
      "windows": [ {"x":..., "y":..., "width":...} ]
    }

Usage:
    python -m scripts.evaluate_dataset /path/to/dataset
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.detection.service import DetectionService  # noqa: E402
from scripts.validate_detection import (  # noqa: E402
    GTWall,
    Plan,
    _wall_iou,
    _wall_match,
)

def _load_plan(sample_dir: Path, img_path: Path) -> Plan:
    gt_path = img_path.with_suffix(".json")
    if not gt_path.exists():
        raise FileNotFoundError(f"Falta el ground truth: {gt_path}")
    gt = json.loads(gt_path.read_text())
    img = cv2.imread(str(img_path))
    assert img is not None, f"No se pudo leer {img_path}"
    h, w = img.shape[:2]
    walls = [GTWall(**w) for w in gt.get("walls", [])]
    return Plan(name=img_path.stem, size=(w, h), walls=walls)


def _report(name: str, tp: int, fp: int, fn: int) -> None:
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print(f"  {name:<12} TP={tp:<3} FP={fp:<3} FN={fn:<3} "
          f"precision={prec:.2f} recall={rec:.2f} F1={f1:.2f}")
    return None


def evaluate(sample_dir: Path, service: DetectionService) -> None:
    images = sorted(list(sample_dir.glob("*.png")) + list(sample_dir.glob("*.jpg")))
    if not images:
        print(f"No hay imágenes en {sample_dir}")
        return

    total_w_tp = total_w_fn = 0
    ious: list[float] = []

    for img_path in images:
        plan = _load_plan(sample_dir, img_path)
        img = cv2.imread(str(img_path))
        line_result, doors, windows = service._process_image_all(img)

        w_tp = sum(1 for gt in plan.walls
                   if any(_wall_match(d, gt) for d in line_result.grouped_lines))
        total_w_tp += w_tp
        total_w_fn += len(plan.walls) - w_tp
        ious.append(_wall_iou(plan, line_result.grouped_lines))

    _report("walls", total_w_tp, 0, total_w_fn)
    print(f"  wall IoU (real) = {np.mean(ious):.3f} (±{np.std(ious):.3f})")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m scripts.evaluate_dataset /ruta/al/dataset")
        sys.exit(1)
    evaluate(Path(sys.argv[1]), DetectionService())


if __name__ == "__main__":
    main()
