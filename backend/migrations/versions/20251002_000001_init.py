"""init

Revision ID: 20251002_000001
Revises: 
Create Date: 2025-10-02 00:00:01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251002_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Core artifact/fact/evidence tables
    op.create_table(
        'artifact',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('filepath', sa.String(), nullable=False),
        sa.Column('filetype', sa.String(), nullable=False),
        sa.Column('report_week', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
    )
    op.create_table(
        'evidence',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('artifact_id', sa.String(), nullable=False),
        sa.Column('locator', sa.String(), nullable=True),
        sa.Column('preview', sa.Text(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('coordinates_json', sa.Text(), nullable=True),
        sa.Column('full_data_json', sa.Text(), nullable=True),
    )
    op.create_table(
        'fact',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('artifact_id', sa.String(), nullable=False),
        sa.Column('report_week', sa.String(), nullable=True),
        sa.Column('entity', sa.String(), nullable=True),
        sa.Column('metrics_json', sa.Text(), nullable=False),
    )

    # Extended LMS schema
    op.create_table(
        'document',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
    )
    op.create_table(
        'section',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('bbox_json', sa.Text(), nullable=True),
    )
    op.create_table(
        'doctable',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('json', sa.Text(), nullable=False),
    )
    op.create_table(
        'apiendpoint',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('tags_json', sa.Text(), nullable=True),
        sa.Column('params_json', sa.Text(), nullable=True),
        sa.Column('responses_json', sa.Text(), nullable=True),
    )
    op.create_table(
        'logentry',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('ts', sa.String(), nullable=True),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('code', sa.String(), nullable=True),
        sa.Column('component', sa.String(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('attrs_json', sa.Text(), nullable=True),
    )
    op.create_table(
        'tagrow',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), nullable=False),
        sa.Column('tag', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('source_ptr', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('tagrow')
    op.drop_table('logentry')
    op.drop_table('apiendpoint')
    op.drop_table('doctable')
    op.drop_table('section')
    op.drop_table('document')
    op.drop_table('fact')
    op.drop_table('evidence')
    op.drop_table('artifact')

