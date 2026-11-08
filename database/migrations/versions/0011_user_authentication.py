"""Add user password hashes and revocable user sessions.

Migration 0001 builds every table from the *current* models with
``create_all``. On a fresh database the password column, the sessions table
and their indexes therefore already exist when this migration runs. Every
step below checks first, so it works on both fresh and older databases.
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    columns = sa.inspect(op.get_bind()).get_columns(table)
    return any(item["name"] == column for item in columns)


def _has_index(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    indexes = sa.inspect(op.get_bind()).get_indexes(table)
    return any(item["name"] == name for item in indexes)


def upgrade():
    if not _has_column("users", "password_hash"):
        op.add_column(
            "users",
            sa.Column("password_hash", sa.String(length=255), nullable=True),
        )

    if not _has_index("users", "uq_users_tenant_email"):
        op.create_index(
            "uq_users_tenant_email",
            "users",
            ["tenant_id", "email"],
            unique=True,
        )

    if not _has_table("user_sessions"):
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
            sa.Column(
                "last_used_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )

    session_indexes = [
        ("ix_user_sessions_tenant_id", ["tenant_id"], False),
        ("ix_user_sessions_user_id", ["user_id"], False),
        ("uq_user_sessions_token_hash", ["token_hash"], True),
        ("ix_user_sessions_tenant_user", ["tenant_id", "user_id"], False),
    ]
    for index_name, columns, unique in session_indexes:
        if not _has_index("user_sessions", index_name):
            op.create_index(
                index_name, "user_sessions", columns, unique=unique
            )


def downgrade():
    if _has_table("user_sessions"):
        for index_name in (
            "ix_user_sessions_tenant_user",
            "uq_user_sessions_token_hash",
            "ix_user_sessions_user_id",
            "ix_user_sessions_tenant_id",
        ):
            if _has_index("user_sessions", index_name):
                op.drop_index(index_name, table_name="user_sessions")
        op.drop_table("user_sessions")

    if _has_index("users", "uq_users_tenant_email"):
        op.drop_index("uq_users_tenant_email", table_name="users")

    if _has_column("users", "password_hash"):
        op.drop_column("users", "password_hash")
