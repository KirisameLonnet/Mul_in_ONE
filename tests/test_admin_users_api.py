"""Integration tests for admin user management endpoints."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from mul_in_one_nemo.db import get_engine
from mul_in_one_nemo.db.models import Base
from mul_in_one_nemo.service import create_app

ROOT_DIR = Path(__file__).resolve().parents[1]

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_admin_api.db")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MUL_IN_ONE_PERSONAS", str(ROOT_DIR / "personas" / "persona.yaml"))
os.environ.setdefault("MUL_IN_ONE_NIM_MODEL", "test-model")
os.environ.setdefault("MUL_IN_ONE_NIM_BASE_URL", "http://localhost")
os.environ.setdefault("MUL_IN_ONE_NEMO_API_KEY", "test-key")
os.environ.setdefault("MUL_IN_ONE_TEMPERATURE", "0.2")
os.environ.setdefault("MUL_IN_ONE_MAX_AGENTS", "3")
os.environ.setdefault("MUL_IN_ONE_MEMORY_WINDOW", "8")
os.environ.setdefault("MUL_IN_ONE_RUNTIME_MODE", "stub")
os.environ.setdefault("MUL_IN_ONE_SESSION_REPO", "memory")


def _reset_database() -> None:
    async def _reset() -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all, checkfirst=True)
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    asyncio.run(_reset())


def _register_user(client: TestClient, *, email: str, username: str, password: str) -> Dict[str, Any]:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "username": username,
            "display_name": username,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload["access_token"]


@pytest.fixture()
def client() -> TestClient:
    _reset_database()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_first_registered_user_is_admin(client: TestClient):
    user = _register_user(
        client,
        email="first@example.com",
        username="first_user",
        password="FirstPass123!",
    )
    assert user["role"] == "admin"
    assert user["is_superuser"] is True


def test_admin_list_and_delete_users(client: TestClient):
    admin_password = "AdminPass123!"
    admin = _register_user(
        client,
        email="admin@example.com",
        username="admin_user",
        password=admin_password,
    )
    other = _register_user(
        client,
        email="user@example.com",
        username="normal_user",
        password="UserPass123!",
    )
    token = _login(client, email=admin["email"], password=admin_password)
    headers = {"Authorization": f"Bearer {token}"}

    list_response = client.get("/api/admin/users", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    delete_response = client.delete(f"/api/admin/users/{other['id']}", headers=headers)
    assert delete_response.status_code == 204

    list_after_delete = client.get("/api/admin/users", headers=headers)
    assert list_after_delete.status_code == 200
    users = list_after_delete.json()
    assert len(users) == 1
    assert users[0]["id"] == admin["id"]

    self_delete_response = client.delete(f"/api/admin/users/{admin['id']}", headers=headers)
    assert self_delete_response.status_code == 400
    assert "无法删除" in self_delete_response.json()["detail"]


def test_admin_can_toggle_privileges(client: TestClient):
    admin_password = "RootAdmin123!"
    admin = _register_user(
        client,
        email="root@example.com",
        username="root_admin",
        password=admin_password,
    )
    user = _register_user(
        client,
        email="member@example.com",
        username="member_user",
        password="MemberPass123!",
    )
    token = _login(client, email=admin["email"], password=admin_password)
    headers = {"Authorization": f"Bearer {token}"}

    promote_resp = client.patch(
        f"/api/admin/users/{user['id']}/admin",
        headers=headers,
        json={"is_admin": True},
    )
    assert promote_resp.status_code == 200
    promoted = promote_resp.json()
    assert promoted["is_superuser"] is True
    assert promoted["role"] == "admin"

    demote_resp = client.patch(
        f"/api/admin/users/{user['id']}/admin",
        headers=headers,
        json={"is_admin": False},
    )
    assert demote_resp.status_code == 200
    demoted = demote_resp.json()
    assert demoted["is_superuser"] is False
    assert demoted["role"] == "member"

    self_demote_resp = client.patch(
        f"/api/admin/users/{admin['id']}/admin",
        headers=headers,
        json={"is_admin": False},
    )
    assert self_demote_resp.status_code == 400
    assert "无法取消" in self_demote_resp.json()["detail"]
