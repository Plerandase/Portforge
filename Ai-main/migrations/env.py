import sys
from os.path import abspath, dirname
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. 프로젝트 루트 경로를 파이썬 경로에 추가 (app을 찾기 위함)
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# 2. 우리 프로젝트의 설정과 베이스 모델 로드
from app.core.config import settings
from app.core.database import Base
from app.models import * # 모든 모델을 로드하여 자동 감지

# Alembic 설정 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# [중요] 자동 감지를 위한 메타데이터 설정
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Offline 모드: DB 연결 없이 SQL 파일 생성 등"""
    # .env에서 가져온 주소를 Alembic에 주입 (aiomysql -> pymysql 호환성 처리 포함)
    url = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
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
    # .env 주소를 가져와서 동기 드라이버(pymysql)로 변환 (Alembic은 동기 방식 사용)
    connect_url = settings.DATABASE_URL.replace("mysql+aiomysql", "mysql+pymysql")
    
    # 설정 객체에 주소 주입
    alembic_config = config.get_section(config.config_ini_section, {})
    alembic_config["sqlalchemy.url"] = connect_url

    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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