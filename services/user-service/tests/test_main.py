"""Tests for the User Service API."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readyz():
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_list_users():
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_user():
    user_data = {
        "name": "Test User",
        "email": "test@example.com",
        "role": "developer",
    }
    response = client.post("/api/v1/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["role"] == "developer"
    assert "id" in data


def test_get_user():
    # Create a user first
    user_data = {"name": "Get Test", "email": "get@test.com", "role": "viewer"}
    create_resp = client.post("/api/v1/users", json=user_data)
    user_id = create_resp.json()["id"]

    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id


def test_get_user_not_found():
    response = client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404


def test_update_user():
    user_data = {"name": "Original", "email": "orig@test.com", "role": "developer"}
    create_resp = client.post("/api/v1/users", json=user_data)
    user_id = create_resp.json()["id"]

    update_resp = client.put(f"/api/v1/users/{user_id}", json={"name": "Updated"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated"


def test_delete_user():
    user_data = {"name": "To Delete", "email": "del@test.com", "role": "developer"}
    create_resp = client.post("/api/v1/users", json=user_data)
    user_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/users/{user_id}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 404
