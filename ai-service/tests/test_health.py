"""Tests for Health and Status endpoints."""

from fastapi.testclient import TestClient


def test_health_check_root(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data
    assert data["active_taxonomy_skills"] > 0
    assert data["active_resource_catalogue_skills"] > 0
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert "X-Process-Time-Ms" in response.headers


def test_health_check_v1(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_redirect(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    assert len(data["endpoints"]) == 4
