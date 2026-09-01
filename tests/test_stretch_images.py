from pathlib import Path
from uuid import uuid4

from PIL import Image

from app.models import (
    ImageAsset,
    Tenant,
)
from app.tenancy import hash_api_key


def tenant_and_key(db):
    key = f"stretch-{uuid4().hex}"

    tenant = Tenant(
        slug=f"stretch-{uuid4().hex}",
        name="Stretch Tenant",
        api_key_hash=hash_api_key(
            key
        ),
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant, key


def test_alt_text_endpoint_uses_vision_caption(
    client,
    db,
):
    tenant, key = tenant_and_key(
        db
    )

    image = ImageAsset(
        tenant_id=tenant.id,
        filename=(
            f"fox-{uuid4().hex}.jpg"
        ),
        path="/tmp/unused.jpg",
        subject="red fox",
        category="animal",
        caption=(
            "A red fox standing "
            "in a snowy forest."
        ),
        confidence=0.95,
        processed=True,
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    response = client.get(
        (
            "/api/v1/images/"
            f"{image.id}/alt-text"
        ),
        headers={
            "X-API-Key": key,
        },
    )

    assert response.status_code == 200

    assert (
        "red fox"
        in response.json()[
            "alt_text"
        ].lower()
    )


def test_duplicate_endpoint_detects_copy(
    client,
    db,
    tmp_path: Path,
):
    tenant, key = tenant_and_key(
        db
    )

    left = (
        tmp_path
        / f"left-{uuid4().hex}.png"
    )

    right = (
        tmp_path
        / f"right-{uuid4().hex}.png"
    )

    image = Image.new(
        "RGB",
        (80, 80),
        "red",
    )

    image.save(left)
    image.save(right)

    first = ImageAsset(
        tenant_id=tenant.id,
        filename=left.name,
        path=str(left),
        processed=True,
    )

    second = ImageAsset(
        tenant_id=tenant.id,
        filename=right.name,
        path=str(right),
        processed=True,
    )

    db.add_all(
        [
            first,
            second,
        ]
    )
    db.commit()

    db.refresh(first)

    response = client.get(
        (
            "/api/v1/images/"
            f"{first.id}/duplicates"
        ),
        headers={
            "X-API-Key": key,
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert len(
        result["duplicates"]
    ) == 1

    assert (
        result["duplicates"][0]
        ["similarity"]
        == 1.0
    )


def test_duplicate_scan_is_tenant_isolated(
    client,
    db,
    tmp_path: Path,
):
    tenant_a, key_a = (
        tenant_and_key(db)
    )

    tenant_b, _ = (
        tenant_and_key(db)
    )

    path = (
        tmp_path
        / f"same-{uuid4().hex}.png"
    )

    Image.new(
        "RGB",
        (80, 80),
        "blue",
    ).save(path)

    first = ImageAsset(
        tenant_id=tenant_a.id,
        filename=(
            f"a-{uuid4().hex}.png"
        ),
        path=str(path),
        processed=True,
    )

    other_tenant = ImageAsset(
        tenant_id=tenant_b.id,
        filename=(
            f"b-{uuid4().hex}.png"
        ),
        path=str(path),
        processed=True,
    )

    db.add_all(
        [
            first,
            other_tenant,
        ]
    )

    db.commit()
    db.refresh(first)

    response = client.get(
        (
            "/api/v1/images/"
            f"{first.id}/duplicates"
        ),
        headers={
            "X-API-Key": key_a,
        },
    )

    assert response.status_code == 200
    assert (
        response.json()[
            "duplicates"
        ]
        == []
    )
