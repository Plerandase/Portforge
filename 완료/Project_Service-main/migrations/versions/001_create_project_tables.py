"""Create Project Service Tables

Revision ID: 001_create_project_tables
Revises: 
Create Date: 2026-01-08

Project 서비스 전용 테이블:
- projects: 프로젝트/스터디 정보
- project_recruitment_positions: 모집 포지션
- applications: 지원서
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '001_create_project_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Project service tables."""
    # Projects 테이블
    op.create_table('projects',
        sa.Column('project_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', mysql.CHAR(length=36), nullable=False, comment='팀장 ID'),
        sa.Column('type', sa.Enum('PROJECT', 'STUDY', name='projecttype'), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('method', sa.Enum('ONLINE', 'OFFLINE', 'MIXED', name='projectmethod'), nullable=False, server_default='ONLINE'),
        sa.Column('status', sa.Enum('RECRUITING', 'PROCEEDING', 'COMPLETED', 'CLOSED', name='projectstatus'), nullable=False, server_default='RECRUITING'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('test_required', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('project_id')
    )
    op.create_index('ix_projects_user_id', 'projects', ['user_id'], unique=False)
    
    # Project Recruitment Positions 테이블
    op.create_table('project_recruitment_positions',
        sa.Column('project_id', sa.BigInteger(), nullable=False),
        sa.Column('position_type', sa.Enum('FRONTEND', 'BACKEND', 'DB', 'INFRA', 'DESIGN', 'ETC', 'STUDY_MEMBER', name='positiontype'), nullable=False),
        sa.Column('required_stacks', sa.Text(), nullable=True, comment='콤마 구분: React,TypeScript'),
        sa.Column('employment_type', sa.String(length=20), nullable=True),
        sa.Column('target_count', sa.Integer(), nullable=True),
        sa.Column('current_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recruitment_deadline', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('project_id', 'position_type')
    )
    
    # Applications 테이블
    op.create_table('applications',
        sa.Column('application_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', mysql.CHAR(length=36), nullable=False),
        sa.Column('position_type', sa.Enum('FRONTEND', 'BACKEND', 'DB', 'INFRA', 'DESIGN', 'ETC', 'STUDY_MEMBER', name='positiontype'), nullable=False),
        sa.Column('prefer_stacks', sa.Text(), nullable=True, comment='콤마 구분 또는 단일 값'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', name='applicationstatus'), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('application_id')
    )
    op.create_index('ix_applications_project_id', 'applications', ['project_id'], unique=False)
    op.create_index('ix_applications_user_id', 'applications', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop Project service tables."""
    op.drop_index('ix_applications_user_id', table_name='applications')
    op.drop_index('ix_applications_project_id', table_name='applications')
    op.drop_table('applications')
    op.drop_table('project_recruitment_positions')
    op.drop_index('ix_projects_user_id', table_name='projects')
    op.drop_table('projects')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS positiontype") 
    op.execute("DROP TYPE IF EXISTS projectstatus")
    op.execute("DROP TYPE IF EXISTS projectmethod")
    op.execute("DROP TYPE IF EXISTS projecttype")
