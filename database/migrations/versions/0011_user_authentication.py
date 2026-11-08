"""Add user password hashes and revocable user sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )

    op.create_index(
        "uq_users_tenant_email",
        "users",
        ["tenant_id", "email"],
        unique=True,
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    op.create_index(
        "ix_user_sessions_tenant_id",
        "user_sessions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_user_sessions_user_id",
        "user_sessions",
        ["user_id"],
    )
    op.create_index(
        "uq_user_sessions_token_hash",
        "user_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_user_sessions_tenant_user",
        "user_sessions",
        ["tenant_id", "user_id"],
    )


def downgrade():
    op.drop_index("ix_user_sessions_tenant_user", table_name="user_sessions")
    op.drop_index("uq_user_sessions_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_tenant_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("uq_users_tenant_email", table_name="users")
    op.drop_column("users", "password_hash")
