"""Staged migration boundary: 0002 request processing.

Schema objects for this stage are currently included in baseline metadata.
Move incremental DDL here when the schema is split into staged releases.
"""
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
