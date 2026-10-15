"""Tests for auth endpoints: register, login, JWT refresh rotation."""
import hashlib
import hmac
import json

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_first_user_becomes_owner(client: AsyncClient):
    """First registered user must get role=owner."""
    response = await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "owner"
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_second_user_locked(client: AsyncClient):
    """Second registration attempt must be rejected with 403."""
    await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    response = await client.post("/api/v1/auth/register", json={"email": "other@test.com", "password": "securepass123"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_valid_credentials(client: AsyncClient):
    """Login with correct credentials returns tokens."""
    await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    response = await client.post("/api/v1/auth/login", json={"email": "owner@test.com", "password": "securepass123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Login with wrong password must return 401."""
    await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    response = await client.post("/api/v1/auth/login", json={"email": "owner@test.com", "password": "wrongpassword"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_jwt_refresh_rotation(client: AsyncClient):
    """Refresh token must rotate: old token no longer works after refresh."""
    reg = await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    old_refresh = reg.json()["refresh_token"]

    # Use the refresh token
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Old refresh token must now be invalid
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_access_token_protects_routes(client: AsyncClient):
    """Protected routes must return 403 without a token."""
    response = await client.get("/api/v1/brand")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    """Authenticated /auth/me returns user data."""
    reg = await client.post("/api/v1/auth/register", json={"email": "owner@test.com", "password": "securepass123"})
    token = reg.json()["access_token"]
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "owner@test.com"
    assert response.json()["role"] == "owner"
