from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_validation_rejects_empty_post():
    response = client.post(
        "/api/v1/posts",
        json={
            "title": "",
            "body": "",
        },
    )

    assert response.status_code == 422
