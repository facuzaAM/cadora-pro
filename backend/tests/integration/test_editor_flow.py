import uuid
from uuid import UUID

import pytest

import app.controllers.editor_controller as ec
from app.database import async_session_factory
from app.detection.schemas import (
    Door,
    DoorDetectionResult,
    LineDetectionResult,
    LineSegment,
    Window,
    WindowDetectionResult,
)
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository


async def _register(client, email: str | None = None) -> str:
    email = email or f"editor_{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Testpass123!", "name": "Editor Test"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _create_project(client, token: str, name: str = "Casa") -> str:
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": name, "description": "Planta baja"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_document(project_id: str) -> None:
    async with async_session_factory() as session:
        await DocumentRepository(session).create(
            project_id=UUID(project_id),
            filename="plano.png",
            file_type="png",
            file_size=128,
            storage_path=f"tests/{project_id}/plano.png",
        )
        await session.commit()


async def _set_project_status(project_id: str, status: str) -> None:
    async with async_session_factory() as session:
        await ProjectRepository(session).update_status(UUID(project_id), status)
        await session.commit()


@pytest.mark.asyncio
async def test_detection_run_requires_document(client):
    token = await _register(client)
    project_id = await _create_project(client, token)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/detection/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_detection_status_mapping(client):
    token = await _register(client)
    project_id = await _create_project(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    assert resp.json() == {"status": "pending"}

    await _set_project_status(project_id, "detection_running")
    resp = await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    assert resp.json() == {"status": "processing"}

    await _set_project_status(project_id, "error")
    resp = await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    assert resp.json() == {"status": "error"}


@pytest.mark.asyncio
async def test_detection_run_starts_processing(client, monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(ec, "_detect_project_background", _noop)

    token = await _register(client)
    project_id = await _create_project(client, token)
    await _add_document(project_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"/api/v1/projects/{project_id}/detection/run",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processing"

    body = (
        await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    ).json()
    assert body["status"] == "processing"


@pytest.mark.asyncio
async def test_failed_detection_surfaces_error_status(client):
    token = await _register(client)
    project_id = await _create_project(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    await _set_project_status(project_id, "error")

    body = (
        await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    ).json()
    assert (
        body["status"] == "error"
    ), "una detección fallida debe reportarse como error y no quedar en 'cargando' para siempre"


@pytest.mark.asyncio
async def test_detection_completed_payload(client):
    token = await _register(client)
    project_id = await _create_project(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "lines": LineDetectionResult(
            lines=[],
            grouped_lines=[
                LineSegment(
                    x1=0, y1=0, x2=100, y2=0, angle=0, length=100,
                    category="horizontal",
                )
            ]
        ).model_dump(mode="json"),
        "doors": DoorDetectionResult(
            doors=[Door(type="single", x=10, y=20, width=80, rotation=0, hinge_x=10, hinge_y=20)]
        ).model_dump(mode="json"),
        "windows": WindowDetectionResult(
            windows=[
                Window(
                    type="fixed", x=30, y=40, width=50, height=60,
                    rotation=0, orientation="horizontal",
                )
            ]
        ).model_dump(mode="json"),
        "ocr_texts": [],
        "ocr_measurements": [],
    }
    async with async_session_factory() as session:
        repo = ProjectRepository(session)
        await repo.set_detection_result(project_id, payload)
        await repo.update_status(project_id, "detection_completed")
        await session.commit()

    resp = await client.get(f"/api/v1/projects/{project_id}/detection", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert len(body["walls"]) == 1
    assert len(body["doors"]) == 1
    assert len(body["windows"]) == 1
