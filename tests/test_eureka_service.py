from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import create_app

def test_report_department_integration_success(tmp_path):
    mock_eureka = AsyncMock()
    mock_eureka.do_service.return_value = {
        "id": 1,
        "name": "IT Support",
        "building": "A"
    }

    test_db = f"sqlite:///{tmp_path}/test.db"
    app = create_app(database_url=test_db, eureka_client=mock_eureka)
    
    client = TestClient(app)

    response = client.get("/reports/1/department-info")

    assert response.status_code == 200
    data = response.json()
    assert data["report_id"] == 1
    assert data["department_info"]["name"] == "IT Support"
    
    mock_eureka.do_service.assert_awaited_once_with(
        app_name="DEPARTMENT-SERVICE",
        service_path="/departments/1",
        return_type="json",
        timeout=3,
    )


def test_report_department_integration_failure(tmp_path):
    mock_eureka = AsyncMock()
    mock_eureka.do_service.side_effect = Exception("Service unavailable")

    test_db = f"sqlite:///{tmp_path}/test.db"
    app = create_app(database_url=test_db, eureka_client=mock_eureka)
    client = TestClient(app)

    response = client.get("/reports/1/department-info")

    assert response.status_code == 503
    assert "Nie udało się połączyć z DEPARTMENT-SERVICE" in response.json()["detail"]