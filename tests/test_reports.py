import pytest
from fastapi.testclient import TestClient

from app.main import create_app



@pytest.fixture(autouse=True)
def isolate_database(tmp_path, monkeypatch) -> None:
    db_file = tmp_path / "test_reports.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

def test_health() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "IT Report Service",
        }


def test_create_report_then_read_it() -> None:
    with TestClient(create_app()) as client:
        payload = {
            "department_id": 1,
            "reported_by": "Alice",
            "report_type": "Hardware",
            "description": "Laptop is not working",
        }
        created = client.post("/reports", json=payload)
        assert created.status_code == 201
        assert created.json()["id"] == 1
        assert created.json()["status"] == "unsolved"

        fetched = client.get("/reports/1")
        assert fetched.status_code == 200
        assert fetched.json()["description"] == payload["description"]


def test_duplicate_report_returns_409_without_changing_state() -> None:
    with TestClient(create_app()) as client:
        payload = {
            "department_id": 1,
            "reported_by": "Alice",
            "report_type": "Hardware",
            "description": "Laptop is not working",
        }
        assert client.post("/reports", json=payload).status_code == 201

        duplicate = client.post("/reports", json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == (
            "Zgłoszenie z takim opisem już istnieje."
        )
        assert len(client.get("/reports").json()) == 1


def test_invalid_data_returns_422_without_changing_state() -> None:
    with TestClient(create_app()) as client:
        invalid_payload = {
            "department_id": 0,
            "reported_by": "Alice",
            "report_type": "Hardware",
            "description": "Laptop is not working",
        }
        response = client.post("/reports", json=invalid_payload)
        assert response.status_code == 422
        assert "detail" in response.json()
        assert client.get("/reports").json() == []


def test_missing_report_returns_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/reports/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Nie znaleziono zgłoszenia."


def test_empty_list_returns_200() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/reports")
        assert response.status_code == 200
        assert response.json() == []

def test_delete_report_returns_204() -> None:
    with TestClient(create_app()) as client:
        payload = {
            "department_id": 1,
            "reported_by": "Alice",
            "report_type": "Hardware",
            "description": "Printer is offline",
        }
        created = client.post("/reports", json=payload)
        report_id = created.json()["id"]

        response = client.delete(f"/reports/{report_id}")
        assert response.status_code == 204

        fetched = client.get(f"/reports/{report_id}")
        assert fetched.status_code == 404


def test_delete_missing_report_returns_404() -> None:
    with TestClient(create_app()) as client:
        response = client.delete("/reports/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Nie znaleziono zgłoszenia."