"""Add section-tag metadata for templates and photos

Revision ID: 002_section_tags
Revises: 001_add_phase2_fields
Create Date: 2025-11-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_section_tags'
down_revision = '001_add_phase2_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('survey_template', sa.Column('section_tags', sa.Text(), nullable=True, server_default='{}'))
    op.add_column('photos', sa.Column('tags', sa.Text(), nullable=True, server_default='[]'))


def downgrade():
    op.drop_column('survey_template', 'section_tags')
    op.drop_column('photos', 'tags')

