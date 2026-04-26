"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("username", sa.String(255)),
        sa.Column("first_name", sa.String(255)),
        sa.Column("last_name", sa.String(255)),
        sa.Column("balance", sa.Numeric(12, 2), server_default="0"),
        sa.Column("free_presentations", sa.Integer(), server_default="1"),
        sa.Column("total_spent", sa.Numeric(12, 2), server_default="0"),
        sa.Column("total_deposited", sa.Numeric(12, 2), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_blocked", sa.Boolean(), server_default="false"),
        sa.Column("last_active", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_super_admin", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "pricing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_type", sa.String(100), nullable=False, unique=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), server_default="so'm"),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        sa.Column("receipt_file_id", sa.Text()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("admin_id", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_status", "transactions", ["status"])

    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200)),
        sa.Column("price", sa.Numeric(12, 2), server_default="0"),
        sa.Column("duration_days", sa.Integer(), server_default="30"),
        sa.Column("max_presentations", sa.Integer(), server_default="0"),
        sa.Column("max_courseworks", sa.Integer(), server_default="0"),
        sa.Column("max_slides", sa.Integer(), server_default="20"),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id")),
        sa.Column("plan_name", sa.String(100)),
        sa.Column("max_presentations", sa.Integer(), server_default="0"),
        sa.Column("presentations_used", sa.Integer(), server_default="0"),
        sa.Column("max_courseworks", sa.Integer(), server_default="0"),
        sa.Column("courseworks_used", sa.Integer(), server_default="0"),
        sa.Column("max_slides", sa.Integer(), server_default="20"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])

    op.create_table(
        "presentation_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_uuid", sa.String(36), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("presentation_type", sa.String(50), server_default="presentation"),
        sa.Column("slide_count", sa.Integer(), server_default="10"),
        sa.Column("answers", sa.Text()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("progress", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("amount_charged", sa.Numeric(12, 2), server_default="0"),
        sa.Column("result_file_id", sa.Text()),
        sa.Column("result_r2_key", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_presentation_tasks_uuid", "presentation_tasks", ["task_uuid"])
    op.create_index("ix_presentation_tasks_user", "presentation_tasks", ["user_id"])
    op.create_index("ix_presentation_tasks_status", "presentation_tasks", ["status"])
    op.create_index("ix_presentation_tasks_telegram", "presentation_tasks", ["telegram_id"])

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50), server_default="general"),
        sa.Column("slide_count", sa.Integer(), server_default="10"),
        sa.Column("price", sa.Numeric(12, 2), server_default="0"),
        sa.Column("colors", sa.String(300), server_default="linear-gradient(135deg,#ff6b35,#f7931e)"),
        sa.Column("file_id", sa.Text(), nullable=False),
        sa.Column("preview_file_id", sa.Text()),
        sa.Column("preview_url", sa.Text()),
        sa.Column("is_premium", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("downloads", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_templates_category", "templates", ["category"])

    op.create_table(
        "ready_works",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("subject", sa.String(200), server_default=""),
        sa.Column("work_type", sa.String(50), server_default="mustaqil_ish"),
        sa.Column("page_count", sa.Integer(), server_default="10"),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("language", sa.String(10), server_default="uz"),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("file_id", sa.Text(), nullable=False),
        sa.Column("preview_file_id", sa.Text()),
        sa.Column("preview_available", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("downloads", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ready_works_type", "ready_works", ["work_type"])

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("channel_username", sa.String(200)),
        sa.Column("channel_name", sa.String(200)),
        sa.Column("is_required", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("channels")
    op.drop_table("ready_works")
    op.drop_table("templates")
    op.drop_table("presentation_tasks")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
    op.drop_table("transactions")
    op.drop_table("pricing")
    op.drop_table("admins")
    op.drop_table("users")
