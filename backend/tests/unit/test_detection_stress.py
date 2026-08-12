"""Regression tests for detection robustness on AI-generated floor plans.

Real AI floor plans differ from clean vector renders: anti-aliased strokes,
JPEG artifacts, blur, noise, a slight tint and occasional rotation. These
tests render the synthetic plans and degrade them the way an AI image or a
photo scan would look, then assert the detector keeps walls/windows/doors
recalled with high precision and, crucially, does not fabricate phantom
windows on noise breaks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.detection.service import DetectionService  # noqa: E402
from scripts.validate_detection import (  # noqa: E402
    _door_match,
    _seg_length,
    _wall_match,
    _window_match,
    build_plans,
)

WALLS_MIN_PREC = 0.95
WALLS_MIN_REC = 0.95
WIN_MIN_PREC = 0.9
WIN_MIN_REC = 0.95
DOOR_MIN_REC = 0.8


def _degrade(img: np.ndarray, seed: int = 7) -> np.ndarray:
    """Blur + JPEG + Gaussian noise, like a compressed AI image / photo."""
    rng = np.random.default_rng(seed)
    out = cv2.GaussianBlur(img, (3, 3), 0)
    ok, enc = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 72])
    assert ok
    decoded = cv2.imdecode(enc, cv2.IMREAD_COLOR)
    assert decoded is not None
    out = decoded
    out = np.clip(out.astype(np.float32) + rng.normal(0, 3.5, out.shape), 0, 255)
    return out.astype(np.uint8)


def _tint(img: np.ndarray, bg: tuple[int, int, int] = (247, 244, 238)) -> np.ndarray:
    """Remap pure-white background to an off-white tint (AI render look)."""
    out = img.astype(np.float32)
    out[out.sum(axis=2) > 740] = bg
    return np.clip(out, 0, 255).astype(np.uint8)


def _rotate(img: np.ndarray, deg: float) -> np.ndarray:
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR,
                          borderValue=(255, 255, 255))


def _metrics(plan, img: np.ndarray, service: DetectionService):
    """Precision/recall of the pipeline on a rendered image."""
    line_result, doors, windows = service._process_image_all(img)

    w_tp = sum(
        1 for gt in plan.walls if any(_wall_match(d, gt) for d in line_result.grouped_lines)
    )
    w_fn = len(plan.walls) - w_tp
    shortest = min(_seg_length(w.x1, w.y1, w.x2, w.y2) for w in plan.walls) if plan.walls else 0.0
    w_fp = sum(
        1 for d in line_result.grouped_lines
        if _seg_length(d.x1, d.y1, d.x2, d.y2) >= shortest * 0.5
        and not any(_wall_match(d, gt) for gt in plan.walls)
    )
    w_prec = w_tp / (w_tp + w_fp) if (w_tp + w_fp) else 0.0
    w_rec = w_tp / (w_tp + w_fn) if (w_tp + w_fn) else 0.0

    d_prec = d_rec = 0.0
    if plan.doors:
        d_tp = sum(1 for gt in plan.doors if any(_door_match(x, gt) for x in doors.doors))
        d_fp = sum(1 for x in doors.doors if not any(_door_match(x, gt) for gt in plan.doors))
        d_prec = d_tp / (d_tp + d_fp) if (d_tp + d_fp) else 0.0
        d_rec = d_tp / len(plan.doors)

    v_prec = v_rec = 0.0
    if plan.windows:
        v_tp = sum(
            1 for gt in plan.windows if any(_window_match(x, gt) for x in windows.windows)
        )
        v_fp = sum(
            1 for x in windows.windows if not any(_window_match(x, gt) for gt in plan.windows)
        )
        v_prec = v_tp / (v_tp + v_fp) if (v_tp + v_fp) else 0.0
        v_rec = v_tp / len(plan.windows)

    return {"walls": (w_prec, w_rec), "doors": (d_prec, d_rec), "windows": (v_prec, v_rec)}


@pytest.fixture(scope="module")
def service() -> DetectionService:
    return DetectionService()


_plans = {p.name: p for p in build_plans()}
_doors_windows = _plans["doors_windows"]


@pytest.mark.parametrize("variant", ["degrade", "tint", "rot12", "rot-08"])
def test_windows_survive_degradation_no_phantoms(service, variant) -> None:
    """Real windows stay detected under degradation without phantom windows.

    Guards the regression where closing bridged a window's two glass lines
    into a solid wall-like block, hiding the opening under JPEG/blur.
    """
    img = _doors_windows.render()
    if variant == "tint":
        img = _tint(_degrade(img))
    elif variant == "rotate" or variant == "rot12":
        img = _degrade(_rotate(img, 1.2))
    elif variant == "rot-08":
        img = _degrade(_rotate(img, -0.8))
    else:
        img = _degrade(img)

    _, _, windows = service._process_image_all(img)
    assert len(windows.windows) == 2
    assert all(w.type.value == "sliding" for w in windows.windows)


@pytest.mark.parametrize("variant", ["degrade", "tint", "rot12", "rot-08"])
def test_detection_precision_under_degradation(service, variant) -> None:
    img = _doors_windows.render()
    if variant == "tint":
        img = _tint(_degrade(img))
    elif variant == "rot12":
        img = _degrade(_rotate(img, 1.2))
    elif variant == "rot-08":
        img = _degrade(_rotate(img, -0.8))
    else:
        img = _degrade(img)

    m = _metrics(_doors_windows, img, service)
    w_prec, w_rec = m["walls"]
    v_prec, v_rec = m["windows"]
    _, d_rec = m["doors"]
    assert w_prec >= WALLS_MIN_PREC and w_rec >= WALLS_MIN_REC
    assert v_prec >= WIN_MIN_PREC and v_rec >= WIN_MIN_REC
    assert d_rec >= DOOR_MIN_REC


def test_interior_walls_survive_degradation(service) -> None:
    """Degradation must not erase walls nor invent doors/windows where there are none."""
    plan = _plans["interior_walls"]
    m = _metrics(plan, _degrade(plan.render()), service)
    assert m["walls"] == (1.0, 1.0)
    assert m["doors"] == (0.0, 0.0)
    assert m["windows"] == (0.0, 0.0)


def _staircase_image(n: int = 8) -> np.ndarray:
    """A shell plus `n` even staircase treads (classic false-wall source)."""
    img = np.full((800, 1100, 3), 255, np.uint8)
    cv2.rectangle(img, (60, 60), (1040, 740), (0, 0, 0), 5)
    y0, x0, x1 = 180, 320, 500
    step = (700 - y0) / n
    for i in range(n):
        y = int(y0 + round(step) * i)
        cv2.line(img, (x0, y), (x1, y), (0, 0, 0), 4)
    return img


def _curve_image() -> np.ndarray:
    """A shell plus a semi-elliptical curved wall (an AI-plan organic shape)."""
    img = np.full((1000, 1400, 3), 255, np.uint8)
    cv2.rectangle(img, (80, 80), (1320, 920), (0, 0, 0), 4)
    cv2.ellipse(img, (700, 500), (300, 160), 0, 0, 180, (0, 0, 0), 4)
    return img


def test_curve_wall_preserved(service) -> None:
    """A curved wall must survive as clean chords, not be dropped as furniture."""
    line_result, _, _ = service._process_image_all(_curve_image())
    diag = [w for w in line_result.grouped_lines if w.category.value == "diagonal"]
    # The semi-ellipse between x~400..1000 yields several diagonal chords.
    in_curve = [w for w in diag if 400 < (w.x1 + w.x2) / 2 < 1000]
    assert len(in_curve) >= 3
    # It must not be removed entirely (regression: was treated as furniture box).
    assert len(diag) >= 3


def test_stairs_not_walls(service) -> None:
    """Repeated parallel stair treads must not become walls."""
    img = _staircase_image(8)
    line_result, _, _ = service._process_image_all(img)
    treads = [
        w for w in line_result.grouped_lines
        if w.category.value == "horizontal" and w.length < 400
    ]
    # All treads removed: only the shell (long) lines remain.
    assert treads == []
