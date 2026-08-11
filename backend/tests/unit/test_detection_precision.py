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
