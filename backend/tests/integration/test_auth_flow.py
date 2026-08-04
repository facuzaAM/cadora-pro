import pytest
from sqlalchemy import func, select

from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def register_user(client, email: str = "user@example.com", password: str = "Testpass123!"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": "Test User"},
    )
    assert resp.status_code == 200
    data = resp.json()
    return data


@pytest.mark.asyncio
async def test_register_login_and_me(client):
    data = await register_user(client)

    assert data["user"]["email"] == "user@example.com"
    assert data["access_token"]

    token = data["access_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Testpass123!"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "user@example.com"

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong"},
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_flow(client):
    await register_user(client)
    resp = await client.post("/api/v1/auth/refresh", json={})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password(client):
    data = await register_user(client)
    token = data["access_token"]

    wrong = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "nope", "new_password": "NuevaPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert wrong.status_code == 400

    ok = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Testpass123!", "new_password": "NuevaPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 204

    login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "Testpass123!"},
    )
    assert login_old.status_code == 400

    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "NuevaPass123!"},
    )
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_export_user_data(client):
    data = await register_user(client)
    token = data["access_token"]

    project = await client.post(
        "/api/v1/projects/",
        json={"name": "Casa", "description": "Planta baja"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert project.status_code == 201

    resp = await client.get("/api/v1/auth/me/export", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["email"] == "user@example.com"
    assert body["subscription"]["plan"] == "free"
    assert len(body["projects"]) == 1
    assert body["projects"][0]["name"] == "Casa"
    assert body["projects"][0]["documents"] == []


@pytest.mark.asyncio
async def test_delete_account_cascades(client, db_session):
    data = await register_user(client)
    token = data["access_token"]

    project = await client.post(
        "/api/v1/projects/",
        json={"name": "Proyecto a borrar"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert project.status_code == 201

    bad = await client.request(
        "DELETE",
        "/api/v1/auth/me",
        json={"password": "wrong"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 400

    resp = await client.request(
        "DELETE",
        "/api/v1/auth/me",
        json={"password": "Testpass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401

    users = (await db_session.execute(select(func.count()).select_from(User))).scalar_one()
    projects = (await db_session.execute(select(func.count()).select_from(Project))).scalar_one()
    tokens = (
        await db_session.execute(select(func.count()).select_from(RefreshToken))
    ).scalar_one()
    assert users == 0
    assert projects == 0
    assert tokens == 0
