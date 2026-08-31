def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_validation_rejects_empty_post(client):
    response = client.post(
        "/api/v1/posts",
        json={
            "title": "",
            "body": "",
        },
    )

    assert response.status_code == 422
