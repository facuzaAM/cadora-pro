import uuid

import pytest

from app.database import async_session_factory
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.detection_worker import _claim_pending_project


async def _seed_user() -> uuid.UUID:
    async with async_session_factory() as session:
        user = await UserRepository(session).create(
            email=f"worker_{uuid.uuid4().hex[:10]}@example.com",
            name="Worker Test",
            hashed_password="x",
        )
        await session.commit()
        return user.id


async def _seed_project(user_id, status: str):
    async with async_session_factory() as session:
        repo = ProjectRepository(session)
        project = await repo.create(user_id, name="Casa")
        await repo.update_status(project.id, status)
        await session.commit()
        return project.id


@pytest.mark.asyncio
async def test_claim_picks_running_project_and_flips_status():
    user_id = await _seed_user()
    project_id = await _seed_project(user_id, "detection_running")

    async with async_session_factory() as session:
        claimed = await _claim_pending_project(session)
        assert claimed == (project_id, user_id)

    async with async_session_factory() as session:
        repo = ProjectRepository(session)
        project = await repo.get_by_id(project_id)
        assert project.status == "detection_processing"


@pytest.mark.asyncio
async def test_claim_does_not_reclaim_inflight_job():
    user_id = await _seed_user()
    await _seed_project(user_id, "detection_processing")

    async with async_session_factory() as session:
        claimed = await _claim_pending_project(session)
        assert claimed is None


@pytest.mark.asyncio
async def test_claim_returns_none_when_no_pending():
    async with async_session_factory() as session:
        claimed = await _claim_pending_project(session)
        assert claimed is None

