"""Staged migration boundary: 0009 idempotency.

Schema objects for this stage are currently included in baseline metadata.
Move incremental DDL here when the schema is split into staged releases.
"""
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
