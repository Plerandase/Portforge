"""Create AI Service Tables

Revision ID: 001_create_ai_tables
Revises: 
Create Date: 2026-01-08

AI 서비스 전용 테이블 (ERD 기준):
- tests: 문제 은행
- test_results: 테스트 결과
- meeting_sessions: 회의 세션 (AI 회의록 생성용)
- generated_reports: AI 생성 리포트
- portfolios: AI 기반 포트폴리오
- meeting_notes: 수동 회의 노트
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_create_ai_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI service tables."""
    # Tests 테이블 (문제 은행)
    op.create_table('tests',
        sa.Column('test_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('stack_name', sa.String(length=50), nullable=False, comment='문제의 카테고리 (React, Java...)'),
        sa.Column('question_json', sa.JSON(), nullable=False, comment='단일 문제 데이터 {q, options, answer, explanation}'),
        sa.Column('difficulty', sa.String(length=20), server_default='초급', nullable=True),
        sa.Column('source_prompt', sa.Text(), nullable=True, comment='생성 시 사용된 프롬프트 (Log용)'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('test_id')
    )
    
    # Test Results 테이블 (테스트 응시 결과)
    op.create_table('test_results',
        sa.Column('result_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=True),
        sa.Column('application_id', sa.BigInteger(), unique=True, nullable=True, comment='1번의 지원 = 1번의 결과'),
        sa.Column('test_type', sa.String(length=20), server_default='APPLICATION', nullable=True),
        sa.Column('score', sa.BigInteger(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('result_id')
    )
    op.create_index('ix_test_results_user_id', 'test_results', ['user_id'], unique=False)
    
    # Generated Reports 테이블 (AI가 생성한 리포트)
    op.create_table('generated_reports',
        sa.Column('report_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('team_id', sa.BigInteger(), nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=True, comment='프로젝트별 회의록 조회 지원'),
        sa.Column('created_by', sa.String(length=36), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False, comment='MEETING_MINUTES, PROJECT_PLAN, WEEKLY_REPORT, PORTFOLIO'),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=True, comment='PENDING, COMPLETED, FAILED - 비동기 생성 상태 추적'),
        sa.Column('model_id', sa.String(length=100), nullable=True, comment='AI 모델 ID 기록용'),
        sa.Column('title', sa.String(length=200), nullable=True, comment='OO월 OO일 회의록 / OO 프로젝트 기획서'),
        sa.Column('s3_key', sa.String(length=1024), nullable=True, comment='S3에 JSON으로 저장된 회의록 내용 경로'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('report_id')
    )
    
    # Meeting Sessions 테이블 (회의 세션 관리)
    op.create_table('meeting_sessions',
        sa.Column('session_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('team_id', sa.BigInteger(), nullable=False),
        sa.Column('project_id', sa.BigInteger(), nullable=True, comment='DynamoDB 채팅 조회용 파티션 키 구성'),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True, comment='종료 시점 기록'),
        sa.Column('status', sa.String(length=20), server_default='IN_PROGRESS', nullable=True),
        sa.Column('generated_report_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['generated_report_id'], ['generated_reports.report_id'], ),
        sa.PrimaryKeyConstraint('session_id')
    )
    
    # Meeting Notes 테이블 (수동 회의 노트)
    op.create_table('meeting_notes',
        sa.Column('note_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('team_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('s3_key', sa.String(length=1024), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.PrimaryKeyConstraint('note_id')
    )
    
    # Portfolios 테이블 (AI 기반 자동 포트폴리오)
    op.create_table('portfolios',
        sa.Column('portfolio_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='누구의 포트폴리오인가'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='어떤 프로젝트 결과물인가'),
        sa.Column('title', sa.String(length=200), server_default='프로젝트 회고록', nullable=True),
        sa.Column('summary', sa.Text(), nullable=True, comment='한 줄 요약'),
        sa.Column('role_description', sa.Text(), nullable=True, comment='내가 맡은 역할 상세'),
        sa.Column('problem_solving', sa.Text(), nullable=True, comment='트러블 슈팅 경험 (회의록 기반 추출)'),
        sa.Column('tech_stack_usage', sa.Text(), nullable=True, comment='사용 기술과 활용 방식'),
        sa.Column('growth_point', sa.Text(), nullable=True, comment='배운 점 및 성장 요소'),
        sa.Column('thumbnail_url', sa.String(length=1024), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('portfolio_id')
    )
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'], unique=False)
    op.create_index('ix_portfolios_project_id', 'portfolios', ['project_id'], unique=False)


def downgrade() -> None:
    """Drop AI service tables."""
    op.drop_index('ix_portfolios_project_id', table_name='portfolios')
    op.drop_index('ix_portfolios_user_id', table_name='portfolios')
    op.drop_table('portfolios')
    op.drop_table('meeting_notes')
    op.drop_table('meeting_sessions')
    op.drop_table('generated_reports')
    op.drop_index('ix_test_results_user_id', table_name='test_results')
    op.drop_table('test_results')
    op.drop_table('tests')
