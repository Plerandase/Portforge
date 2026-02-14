"""Create Team Service Tables

Revision ID: 001_create_team_tables
Revises: 
Create Date: 2026-01-08

Team 서비스 전용 테이블 (ERD 기준):
- teams: 팀 정보
- team_members: 팀 멤버

추가 (기존 모델에서 사용):
- tasks: 칸반 태스크
- shared_files: 공유 파일
- invitations: 초대 링크
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '001_create_team_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Team service tables."""
    # Teams 테이블
    op.create_table('teams',
        sa.Column('team_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.BigInteger(), unique=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('s3_key', sa.String(length=1024), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('team_id')
    )
    op.create_index('ix_teams_project_id', 'teams', ['project_id'], unique=True)
    
    # Team Members 테이블
    op.create_table('team_members',
        sa.Column('team_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.Enum('LEADER', 'MEMBER', name='teamrole'), nullable=True, server_default='MEMBER'),
        sa.Column('position_type', sa.Enum('FRONTEND', 'BACKEND', 'DB', 'INFRA', 'DESIGN', 'ETC', name='stackcategory_team'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.team_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('team_id', 'user_id')
    )
    
    # Tasks 테이블 (칸반 보드용 - 기존 모델에서 사용)
    op.create_table('tasks',
        sa.Column('task_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('TODO', 'IN_PROGRESS', 'DONE', name='taskstatus'), server_default='TODO', nullable=True),
        sa.Column('priority', sa.Enum('HIGH', 'MEDIUM', 'LOW', name='taskpriority'), server_default='MEDIUM', nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('assignee_id', sa.String(length=36), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('task_id')
    )
    op.create_index('ix_tasks_project_id', 'tasks', ['project_id'], unique=False)
    
    # Shared Files 테이블 (기존 모델에서 사용)
    op.create_table('shared_files',
        sa.Column('file_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=False),
        sa.Column('team_id', sa.BigInteger(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_url', sa.String(length=1024), nullable=False),
        sa.Column('s3_key', sa.String(length=1024), nullable=False),
        sa.Column('uploaded_by', sa.String(length=36), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('file_id')
    )
    
    # Invitations 테이블 (기존 모델에서 사용)
    op.create_table('invitations',
        sa.Column('invitation_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=False),
        sa.Column('invitation_code', sa.String(length=20), unique=True, nullable=False),
        sa.Column('invitation_link', sa.String(length=1024), nullable=False),
        sa.Column('invited_by', sa.String(length=36), nullable=False),
        sa.Column('position_type', sa.Enum('FRONTEND', 'BACKEND', 'DB', 'INFRA', 'DESIGN', 'ETC', name='stackcategory_team'), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Integer(), server_default='0', nullable=True),
        sa.Column('used_by', sa.String(length=36), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('invitation_id')
    )


def downgrade() -> None:
    """Drop Team service tables."""
    op.drop_table('invitations')
    op.drop_table('shared_files')
    op.drop_index('ix_tasks_project_id', table_name='tasks')
    op.drop_table('tasks')
    op.drop_table('team_members')
    op.drop_index('ix_teams_project_id', table_name='teams')
    op.drop_table('teams')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS taskpriority")
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS stackcategory_team")
    op.execute("DROP TYPE IF EXISTS teamrole")
