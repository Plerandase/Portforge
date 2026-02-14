"""Create Auth Service Tables

Revision ID: 001_create_auth_tables
Revises: 
Create Date: 2026-01-08

Auth 서비스 전용 테이블:
- users: 사용자 정보
- user_stacks: 사용자 기술 스택
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '001_create_auth_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Auth service tables."""
    # Users 테이블
    op.create_table('users',
        sa.Column('user_id', mysql.CHAR(length=36), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('nickname', sa.String(length=20), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ADMIN', name='userrole'), nullable=True, server_default='USER'),
        sa.Column('profile_image_url', sa.Text(), nullable=True),
        sa.Column('liked_project_ids', sa.JSON(), nullable=True, comment='Array: [1, 20, 55]'),
        sa.Column('test_count', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='프로필 수정 일시'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )
    
    # User Stacks 테이블
    op.create_table('user_stacks',
        sa.Column('stack_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', mysql.CHAR(length=36), nullable=False),
        sa.Column('position_type', sa.Enum('FRONTEND', 'BACKEND', 'DB', 'INFRA', 'DESIGN', 'ETC', name='stackcategory'), nullable=False),
        sa.Column('stack_name', sa.Enum(
            'React', 'Vue', 'Nextjs', 'Svelte', 'Angular', 'TypeScript', 'JavaScript',
            'TailwindCSS', 'StyledComponents', 'Redux', 'Recoil', 'Vite', 'Webpack',
            'Java', 'Spring', 'Nodejs', 'Nestjs', 'Go', 'Python', 'Django', 'Flask',
            'Express', 'PHP', 'Laravel', 'GraphQL', 'RubyOnRails', 'CSharp', 'DotNET',
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQLite', 'MariaDB',
            'Cassandra', 'DynamoDB', 'Firebase', 'Firestore', 'Prisma',
            'AWS', 'Docker', 'Kubernetes', 'GCP', 'Azure', 'Terraform', 'Jenkins',
            'GithubActions', 'Nginx', 'Linux', 'Vercel', 'Netlify',
            'Figma', 'AdobeXD', 'Sketch', 'Canva', 'Photoshop', 'Illustrator', 'Blender',
            'UIUXDesign', 'Branding',
            'Git', 'Slack', 'Jira', 'Notion', 'Discord', 'Postman', 'Swagger', 'Zeplin',
            name='techstack'
        ), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('stack_id')
    )
    op.create_index('ix_user_stacks_user_id', 'user_stacks', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop Auth service tables."""
    op.drop_index('ix_user_stacks_user_id', table_name='user_stacks')
    op.drop_table('user_stacks')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS techstack")
    op.execute("DROP TYPE IF EXISTS stackcategory")
    op.execute("DROP TYPE IF EXISTS userrole")
