"""Integration tests for LAB4 API Gateway (Report Service & Department Service)."""

import os

import httpx
import pytest

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8080")

@pytest.fixture
def client():
    with httpx.Client(
        base_url=GATEWAY_URL,
        timeout=10.0,
        trust_env=False,
    ) as http:
        yield http


def test_gateway_process_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "API-GATEWAY"}


def test_report_route_and_header(client):
    response = client.get("/api/reports/1")
    assert response.headers.get("x-gateway") == "lab4"
    assert response.status_code in {200, 404}
    if response.status_code == 200:
        assert "id" in response.json()


def test_department_route_calls_dependency(client):
    response = client.get("/api/departments/1")
    assert response.headers.get("x-gateway") == "lab4"
    assert response.status_code in {200, 404}


def test_domain_404_is_forwarded(client):
    response = client.get("/api/reports/UNKNOWN_ID")
    assert response.status_code == 404
    assert response.headers.get("x-gateway") == "lab4"
    assert "detail" in response.json()


def test_unknown_route_is_not_forwarded(client):
    response = client.get("/not-a-route")
    assert response.status_code == 404
    assert "x-gateway" not in response.headers