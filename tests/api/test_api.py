"""Tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from netopshub.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestAPI:
    def test_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_list_devices(self, client):
        response = client.get("/api/v1/devices")
        assert response.status_code == 200
        assert "devices" in response.json()

    def test_get_topology(self, client):
        response = client.get("/api/v1/topology")
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "links" in data

    def test_chat(self, client):
        response = client.post("/api/v1/chat", json={"message": "Hello"})
        assert response.status_code == 200
        assert "response" in response.json()

    def test_chat_bgp(self, client):
        response = client.post("/api/v1/chat", json={"message": "Why is BGP flapping?"})
        assert response.status_code == 200
        assert len(response.json()["response"]) > 0

    def test_compliance_status(self, client):
        response = client.get("/api/v1/compliance/status")
        assert response.status_code == 200

    def test_sla_status(self, client):
        response = client.get("/api/v1/sla")
        assert response.status_code == 200

    def test_agents_status(self, client):
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert "discovery" in data
        assert "diagnosis" in data
