"""Create Support Communication Service Tables

Revision ID: 001_create_support_tables
Revises: 
Create Date: 2026-01-08

Support 서비스 전용 테이블 (ERD 기준):
- project_reports: 프로젝트 신고/문의
- notifications: 알림
- notices: 공지사항
- banners: 배너
- events: 이벤트 (공모전, 해커톤)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_create_support_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Support service tables."""
    # Project Reports 테이블 (신고/문의)
    op.create_table('project_reports',
        sa.Column('report_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='신고자'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='신고 대상 프로젝트'),
        sa.Column('type', sa.Enum('REPORT', 'INQUIRY', 'BUG', name='projectreporttype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED', name='projectreportstatus'), server_default='PENDING', nullable=False),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index('ix_project_reports_user_id', 'project_reports', ['user_id'], unique=False)
    op.create_index('ix_project_reports_project_id', 'project_reports', ['project_id'], unique=False)
    
    # Notifications 테이블
    op.create_table('notifications',
        sa.Column('notification_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('link', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('notification_id')
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)
    
    # Notices 테이블 (공지사항)
    op.create_table('notices',
        sa.Column('notice_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('notice_id')
    )
    
    # Banners 테이블
    op.create_table('banners',
        sa.Column('banner_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('link', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('banner_id')
    )
    
    # Events 테이블 (공모전, 해커톤)
    op.create_table('events',
        sa.Column('event_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('category', sa.Enum('CONTEST', 'HACKATHON', name='eventcategory'), nullable=True),
        sa.Column('event_description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('event_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )


def downgrade() -> None:
    """Drop Support service tables."""
    op.drop_table('events')
    op.drop_table('banners')
    op.drop_table('notices')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('ix_project_reports_project_id', table_name='project_reports')
    op.drop_index('ix_project_reports_user_id', table_name='project_reports')
    op.drop_table('project_reports')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS eventcategory")
    op.execute("DROP TYPE IF EXISTS projectreportstatus")
    op.execute("DROP TYPE IF EXISTS projectreporttype")
