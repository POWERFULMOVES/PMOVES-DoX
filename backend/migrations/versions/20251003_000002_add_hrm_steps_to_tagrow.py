"""add hrm_steps to tagrow and backfill

Revision ID: 20251003_000002
Revises: 20251002_000001
Create Date: 2025-10-03 00:00:02

"""
from alembic import op
import sqlalchemy as sa


revision = '20251003_000002'
down_revision = '20251002_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('tagrow') as batch:
        batch.add_column(sa.Column('hrm_steps', sa.Integer(), nullable=True))
    # backfill from legacy encoding in source_ptr if present
    conn = op.get_bind()
    try:
        conn.exec_driver_sql(
            """
            UPDATE tagrow
            SET hrm_steps = CAST(REPLACE(source_ptr, 'hrm-refined:steps', '') AS INTEGER)
            WHERE source_ptr LIKE 'hrm-refined:steps%'
            """
        )
    except Exception:
        pass


def downgrade() -> None:
    with op.batch_alter_table('tagrow') as batch:
        batch.drop_column('hrm_steps')

