"""initial tenant-aware schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_tenants_slug",
        "tenants",
        ["slug"],
        unique=True,
    )

    op.create_index(
        "ix_tenants_api_key",
        "tenants",
        ["api_key"],
        unique=True,
    )

    op.create_table(
        "images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("subject", sa.String(255)),
        sa.Column("category", sa.String(100)),
        sa.Column("attributes_json", sa.Text()),
        sa.Column("caption", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("embedding_json", sa.Text()),
        sa.Column("alt_text", sa.Text()),
        sa.Column("perceptual_hash", sa.String(128)),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_images_tenant_id", "images", ["tenant_id"])
    op.create_index("ix_images_filename", "images", ["filename"], unique=True)
    op.create_index("ix_images_subject", "images", ["subject"])
    op.create_index("ix_images_category", "images", ["category"])
    op.create_index("ix_images_perceptual_hash", "images", ["perceptual_hash"])

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("expected_subject", sa.String(255)),
        sa.Column("expected_category", sa.String(100)),
        sa.Column("embedding_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_posts_tenant_id", "posts", ["tenant_id"])

    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("image_id", sa.Integer(), sa.ForeignKey("images.id")),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("accepted_by_guard", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("human_decision", sa.String(32)),
        sa.Column("human_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_suggestions_tenant_id", "suggestions", ["tenant_id"])
    op.create_index("ix_suggestions_post_id", "suggestions", ["post_id"])
    op.create_index("ix_suggestions_image_id", "suggestions", ["image_id"])
    op.create_index(
        "ix_suggestion_post_image",
        "suggestions",
        ["post_id", "image_id"],
    )

    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("kind", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_background_jobs_tenant_id",
        "background_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_background_jobs_status",
        "background_jobs",
        ["status"],
    )

    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id")),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_ai_usage_tenant_id", "ai_usage", ["tenant_id"])
    op.create_index("ix_ai_usage_operation", "ai_usage", ["operation"])


def downgrade():
    op.drop_table("ai_usage")
    op.drop_table("background_jobs")
    op.drop_table("suggestions")
    op.drop_table("posts")
    op.drop_table("images")
    op.drop_table("tenants")
