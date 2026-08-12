"""Admin stats include detection quality aggregates from project JSONB."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.database import async_session_factory
from app.models.project import Project
from app.models.user import User


async def _register(client, email: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Testpass123!", "name": "Admin"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _set_admin(email: str, admin: bool = True) -> None:
    async with async_session_factory() as session:
        user = (await session.execute(
            select(User).where(User.email == email)
        )).scalar_one()
        user.is_admin = admin
        await session.commit()


async def _add_project_with_result(user_email: str, confidence: float) -> None:
    async with async_session_factory() as session:
        user = (await session.execute(
            select(User).where(User.email == user_email)
        )).scalar_one()
        project = Project(
            user_id=user.id,
            name="p",
            status="detection_completed",
            conversion_charged=True,
            detection_result={
                "lines": {"lines": [], "grouped_lines": []},
                "doors": {"doors": []},
                "windows": {"windows": []},
                "ocr_texts": [],
                "image_width": 100,
                "image_height": 100,
                "quality": {"walls": 1, "doors": 0, "windows": 0,
                            "confidence_avg": confidence, "processing_ms": 500,
                            "failed": False},
            },
        )
        session.add(project)
        await session.commit()


@pytest.mark.asyncio
async def test_admin_stats_aggregates_detection_quality(client) -> None:
    email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    token = await _register(client, email)
    await _set_admin(email, True)
    await _add_project_with_result(email, 0.7)
    await _add_project_with_result(email, 0.9)

    resp = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["detected_projects"] == 2
    assert body["avg_detection_confidence"] == round((0.7 + 0.9) / 2, 3)
    assert body["total_detected_elements"] == 2  # 1 wall each


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client) -> None:
    email = f"plain_{uuid.uuid4().hex[:8]}@example.com"
    token = await _register(client, email)  # not admin
    resp = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
