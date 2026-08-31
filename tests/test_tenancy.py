from uuid import uuid4

from app.models import Tenant
from app.tenancy import hash_api_key


def create_tenant(db, key: str) -> Tenant:
    token = uuid4().hex

    tenant = Tenant(
        slug=f"tenant-{token}",
        name=f"Tenant {token}",
        api_key_hash=hash_api_key(key),
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def test_invalid_api_key_is_rejected(client):
    response = client.get(
        "/api/v1/images",
        headers={
            "X-API-Key": "invalid-key",
        },
    )

    assert response.status_code == 401


def test_same_filename_is_isolated_between_tenants(
    client,
    db,
):
    key_a = f"a-{uuid4().hex}"
    key_b = f"b-{uuid4().hex}"

    create_tenant(db, key_a)
    create_tenant(db, key_b)

    filename = f"shared-{uuid4().hex}.jpg"

    payload = {
        "filename": filename,
        "path": f"/tmp/{filename}",
    }

    response_a = client.post(
        "/api/v1/images",
        headers={
            "X-API-Key": key_a,
        },
        json=payload,
    )

    response_b = client.post(
        "/api/v1/images",
        headers={
            "X-API-Key": key_b,
        },
        json=payload,
    )

    assert response_a.status_code == 201
    assert response_b.status_code == 201

    images_a = client.get(
        "/api/v1/images",
        headers={
            "X-API-Key": key_a,
        },
    ).json()

    images_b = client.get(
        "/api/v1/images",
        headers={
            "X-API-Key": key_b,
        },
    ).json()

    assert sum(
        image["filename"] == filename
        for image in images_a
    ) == 1

    assert sum(
        image["filename"] == filename
        for image in images_b
    ) == 1


def test_cross_tenant_post_access_returns_404(
    client,
    db,
):
    key_a = f"a-{uuid4().hex}"
    key_b = f"b-{uuid4().hex}"

    create_tenant(db, key_a)
    create_tenant(db, key_b)

    response = client.post(
        "/api/v1/posts",
        headers={
            "X-API-Key": key_a,
        },
        json={
            "title": "Private fox post",
            "body": "A red fox in a forest.",
            "expected_subject": "red fox",
            "expected_category": "animal",
        },
    )

    assert response.status_code == 201

    post_id = response.json()["id"]

    cross = client.get(
        f"/api/v1/posts/{post_id}/images",
        headers={
            "X-API-Key": key_b,
        },
    )

    assert cross.status_code == 404


def test_job_enqueue_is_idempotent(
    client,
    db,
):
    key = f"job-{uuid4().hex}"
    create_tenant(db, key)

    idem = f"idem-{uuid4().hex}"

    headers = {
        "X-API-Key": key,
        "Idempotency-Key": idem,
    }

    first = client.post(
        "/api/v1/jobs/process-images",
        headers=headers,
    )

    second = client.post(
        "/api/v1/jobs/process-images",
        headers=headers,
    )

    assert first.status_code == 202
    assert second.status_code == 202

    assert (
        first.json()["job_id"]
        == second.json()["job_id"]
    )

    assert first.json()["idempotent"] is False
    assert second.json()["idempotent"] is True
