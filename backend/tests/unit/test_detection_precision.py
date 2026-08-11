"""Precision/recall regression tests for the detection pipeline.

Renders synthetic floor plans with known ground truth and asserts the
detector keeps both precision and recall high. Guards against regressions
like the one that erased walls during preprocessing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.detection.schemas import WindowType  # noqa: E402
from app.detection.service import DetectionService  # noqa: E402
from scripts.validate_detection import build_plans, validate_plan  # noqa: E402

WALL_MIN_PRECISION = 0.95
WALL_MIN_RECALL = 0.95
FEATURE_MIN_RECALL = 0.9


@pytest.fixture(scope="module")
def service() -> DetectionService:
    return DetectionService()


@pytest.mark.parametrize("plan", build_plans(), ids=lambda p: p.name)
def test_plan_precision_recall(service: DetectionService, plan) -> None:
    metrics = validate_plan(plan, service)

    w_prec, w_rec = metrics["walls"]
    assert w_prec >= WALL_MIN_PRECISION, f"walls precision {w_prec:.2f} < {WALL_MIN_PRECISION}"
    assert w_rec >= WALL_MIN_RECALL, f"walls recall {w_rec:.2f} < {WALL_MIN_RECALL}"

    if plan.doors:
        _, d_rec = metrics["doors"]
        assert d_rec >= FEATURE_MIN_RECALL, f"doors recall {d_rec:.2f} < {FEATURE_MIN_RECALL}"

    if plan.windows:
        _, win_rec = metrics["windows"]
        assert win_rec >= FEATURE_MIN_RECALL, f"windows recall {win_rec:.2f} < {FEATURE_MIN_RECALL}"


def test_grid_removed_but_walls_kept(service: DetectionService) -> None:
    """The grid-lattice remover must erase the background without eating walls."""
    plan = next(p for p in build_plans() if p.name == "grid_background")
    metrics = validate_plan(plan, service)

    w_prec, w_rec = metrics["walls"]
    assert w_prec >= WALL_MIN_PRECISION
    assert w_rec >= WALL_MIN_RECALL
    # All GT walls are full-length; no false wall may be as long as a wall.
    assert metrics["walls"] == (1.0, 1.0)


def test_double_wall_plan_perfect(service: DetectionService) -> None:
    """CAD-style double-line walls must keep openings without phantoms.

    Guards against two regressions found while adding the plan: the merged
    centreline (no ink) triggering phantom windows, and short door leaves
    vanishing from the Hough pass on large images.
    """
    plan = next(p for p in build_plans() if p.name == "double_walls")
    metrics = validate_plan(plan, service)

    assert metrics["walls"] == (1.0, 1.0)
    assert metrics["doors"] == (1.0, 1.0)
    assert metrics["windows"] == (1.0, 1.0)


def test_text_labels_not_walls(service: DetectionService) -> None:
    """Room labels must not collapse into false wall lines."""
    plan = next(p for p in build_plans() if p.name == "text_annotations")
    metrics = validate_plan(plan, service)

    assert metrics["walls"] == (1.0, 1.0)
    assert metrics["doors"] == (0.0, 0.0)
    assert metrics["windows"] == (0.0, 0.0)


def test_two_glass_lines_classify_as_sliding(service: DetectionService) -> None:
    """CAD windows draw two thin glass lines; both must read as SLIDING."""
    plan = next(p for p in build_plans() if p.name == "doors_windows")
    _, _, windows = service._process_image_all(plan.render())

    assert len(windows.windows) == 2
    assert all(w.type == WindowType.SLIDING for w in windows.windows)


def test_aligned_plan_not_rotated_by_deskew() -> None:
    """An already-axis-aligned plan must pass through deskew unchanged.

    Regression guard for the phantom-window bug: the skew estimator voted on
    the white background and then, due to 1-deg theta quantisation, reported
    ~1.5 deg of skew on an aligned plan, rotating it and fabricating windows.
    """
    import numpy as np

    from app.ocr.preprocessor import ImagePreprocessor

    plan = next(p for p in build_plans() if p.name == "doors_windows")
    binary = ImagePreprocessor().detect_pipeline(plan.render())

    assert ImagePreprocessor._estimate_skew(binary) == pytest.approx(0.0, abs=0.05)
    # Deskew must be a no-op: rotating 0.25 deg a second time is the trigger
    # that used to corrupt an aligned plan.
    assert np.array_equal(binary, ImagePreprocessor().deskew(binary))


def test_deskew_recovers_small_rotation() -> None:
    """A slightly rotated plan is straightened back to axis-alignment."""
    import cv2

    from app.ocr.preprocessor import ImagePreprocessor

    plan = next(p for p in build_plans() if p.name == "doors_windows")
    img = plan.render()
    h, w = img.shape[:2]
    for deg in (0.5, 1.5, -1.0):
        matrix = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
        rotated = cv2.warpAffine(
            img, matrix, (w, h),
            flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255),
        )
        binary = ImagePreprocessor().detect_pipeline(rotated)
        residual = ImagePreprocessor._estimate_skew(binary)
        assert abs(residual) < 0.15, (
            f"skew {deg} deg left {residual:.3f} deg residual"
        )
