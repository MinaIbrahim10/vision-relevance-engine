import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Tenant


DEFAULT_TENANT_SLUG = "demo"


def ensure_demo_tenant(db: Session) -> Tenant:
    tenant = (
        db.query(Tenant)
        .filter(Tenant.slug == DEFAULT_TENANT_SLUG)
        .first()
    )

    if tenant:
        return tenant

    tenant = Tenant(
        slug=DEFAULT_TENANT_SLUG,
        name="Demo Tenant",
        api_key="demo-local-key",
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
    # Local demo remains easy to run.
    if not x_api_key:
        return ensure_demo_tenant(db)

    tenant = (
        db.query(Tenant)
        .filter(Tenant.api_key == x_api_key)
        .first()
    )

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Invalid tenant API key",
        )

    return tenant


def create_api_key() -> str:
    return secrets.token_urlsafe(32)
