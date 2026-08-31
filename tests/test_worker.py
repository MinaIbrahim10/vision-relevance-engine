from uuid import uuid4

from app.db import SessionLocal
from app.models import (
    BackgroundJob,
    ImageAsset,
    JobAlert,
    Tenant,
)
from app.services import pipeline
from app.services.pipeline import process_images_job
from app.tenancy import hash_api_key


def create_tenant(db):
    token = uuid4().hex

    tenant = Tenant(
        slug=f"worker-{token}",
        name="Worker Tenant",
        api_key_hash=hash_api_key(token),
    )

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def test_worker_processes_only_its_tenant(db):
    tenant_a = create_tenant(db)
    tenant_b = create_tenant(db)

    fox = ImageAsset(
        tenant_id=tenant_a.id,
        filename=f"fox-{uuid4().hex}.jpg",
        path="/tmp/red_fox_01.jpg",
        processed=False,
    )

    wolf = ImageAsset(
        tenant_id=tenant_b.id,
        filename=f"wolf-{uuid4().hex}.jpg",
        path="/tmp/wolf_01.jpg",
        processed=False,
    )

    db.add_all([fox, wolf])

    job = BackgroundJob(
        tenant_id=tenant_a.id,
        kind="image_processing",
        idempotency_key=f"job-{uuid4().hex}",
        status="queued",
        max_attempts=3,
    )

    db.add(job)
    db.commit()

    process_images_job(
        SessionLocal,
        job.id,
    )

    db.expire_all()

    fox_after = db.get(
        ImageAsset,
        fox.id,
    )

    wolf_after = db.get(
        ImageAsset,
        wolf.id,
    )

    job_after = db.get(
        BackgroundJob,
        job.id,
    )

    assert fox_after.processed is True
    assert wolf_after.processed is False
    assert job_after.status == "completed"


def test_worker_retries_then_emits_failure_alert(
    db,
    monkeypatch,
):
    owner = create_tenant(db)

    image = ImageAsset(
        tenant_id=owner.id,
        filename=f"broken-{uuid4().hex}.jpg",
        path="/tmp/broken.jpg",
        processed=False,
    )

    job = BackgroundJob(
        tenant_id=owner.id,
        kind="image_processing",
        idempotency_key=f"failure-{uuid4().hex}",
        status="queued",
        max_attempts=2,
    )

    db.add_all([image, job])
    db.commit()

    def fail(*args, **kwargs):
        raise RuntimeError(
            "synthetic provider failure"
        )

    monkeypatch.setattr(
        pipeline,
        "process_single_image",
        fail,
    )

    process_images_job(
        SessionLocal,
        job.id,
    )

    db.expire_all()

    first = db.get(
        BackgroundJob,
        job.id,
    )

    assert first.status == "retry"
    assert first.attempts == 1

    process_images_job(
        SessionLocal,
        job.id,
    )

    db.expire_all()

    final = db.get(
        BackgroundJob,
        job.id,
    )

    alerts = (
        db.query(JobAlert)
        .filter(
            JobAlert.job_id == job.id
        )
        .all()
    )

    assert final.status == "failed"
    assert final.attempts == 2

    assert any(
        alert.level == "warning"
        for alert in alerts
    )

    assert any(
        alert.level == "error"
        for alert in alerts
    )
