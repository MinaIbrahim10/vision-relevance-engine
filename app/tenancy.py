import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Tenant


DEFAULT_TENANT_SLUG = "demo"


def hash_api_key(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def create_api_key() -> str:
    return secrets.token_urlsafe(32)


def ensure_demo_tenant(
    db: Session,
) -> Tenant:
    settings = get_settings()

    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.slug == DEFAULT_TENANT_SLUG
        )
        .first()
    )

    if tenant:
        return tenant

    tenant = Tenant(
        slug=DEFAULT_TENANT_SLUG,
        name="Demo Tenant",
        api_key_hash=hash_api_key(
            settings.demo_api_key
        ),
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def get_tenant(
    x_api_key: str | None = Header(
        default=None,
        alias="X-API-Key",
    ),
    db: Session = Depends(get_db),
) -> Tenant:
    settings = get_settings()

    if not x_api_key:
        if settings.app_env in {
            "development",
            "test",
        }:
            return ensure_demo_tenant(db)

        raise HTTPException(
            status_code=401,
            detail="X-API-Key is required",
        )

    key_hash = hash_api_key(x_api_key)

    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.api_key_hash == key_hash
        )
        .first()
    )

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Invalid tenant API key",
        )

    return tenant
