"""Add Phase 2 features: conditional logic, photo requirements, and progress tracking

Revision ID: 001_add_phase2_fields
Revises: 
Create Date: 2025-11-16 22:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_add_phase2_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to template_fields table
    op.add_column('template_fields', sa.Column('conditions', sa.Text(), nullable=True))
    op.add_column('template_fields', sa.Column('photo_requirements', sa.Text(), nullable=True))
    op.add_column('template_fields', sa.Column('section_weight', sa.Integer(), nullable=True, default=1))
    
    # Add new columns to photos table
    op.add_column('photos', sa.Column('requirement_id', sa.String(), nullable=True))
    op.add_column('photos', sa.Column('fulfills_requirement', sa.Boolean(), nullable=True, default=False))
    
    # Add new columns to survey_response table for better tracking
    op.add_column('survey_response', sa.Column('question_id', sa.Integer(), nullable=True))
    op.add_column('survey_response', sa.Column('field_type', sa.String(50), nullable=True))


def downgrade():
    # Remove columns from template_fields table
    op.drop_column('template_fields', 'conditions')
    op.drop_column('template_fields', 'photo_requirements')
    op.drop_column('template_fields', 'section_weight')
    
    # Remove columns from photos table
    op.drop_column('photos', 'requirement_id')
    op.drop_column('photos', 'fulfills_requirement')
    
    # Remove columns from survey_response table
    op.drop_column('survey_response', 'question_id')
    op.drop_column('survey_response', 'field_type')