import sys
from os.path import abspath, dirname
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# 프로젝트 루트 경로 추가
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.core.database import Base
from app.models import *  # 모든 모델 import

# Alembic Config object
config = context.config

# Python logging 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 자동 감지를 위한 메타데이터
target_metadata = Base.metadata


def get_sync_database_url() -> str:
    """
    settings.DATABASE_URL에서 가져와서 동기 드라이버로 변환
    """
    from app.core.config import settings
    url = settings.DATABASE_URL
    if url and "aiomysql" in url:
        url = url.replace("aiomysql", "pymysql")
    return url


def run_migrations_offline() -> None:
    """Offline 모드: DB 연결 없이 SQL 스크립트 생성"""
    url = get_sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online 모드: 실제 DB에 접속하여 마이그레이션 실행"""
    url = get_sync_database_url()
    
    # 동기 엔진 생성
    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args={
            "charset": "utf8mb4"
        }
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()