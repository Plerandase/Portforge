from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv

# 1. .env 환경변수 로딩
load_dotenv()

# 2. 내 앱의 Base와 User 모델 가져오기 (이게 없으면 테이블 안 만들어짐!)
from app.db.session import Base
import app.models.user 

# Alembic 설정 객체
config = context.config

# 3. alembic.ini 대신 .env의 DATABASE_URL 사용하도록 강제 설정
# Alembic은 동기 드라이버를 사용해야 하므로 aiomysql을 pymysql로 변경
if os.getenv("DATABASE_URL"):
    database_url = os.getenv("DATABASE_URL")
    # aiomysql을 pymysql로 변경 (Alembic은 동기 드라이버 필요)
    if "aiomysql" in database_url:
        database_url = database_url.replace("mysql+aiomysql://", "mysql+pymysql://")
    config.set_main_option("sqlalchemy.url", database_url)

# 로그 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 4. 타겟 메타데이터 연결
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """오프라인 모드: DB 연결 없이 SQL만 생성할 때"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """온라인 모드: 실제 DB에 연결해서 작업할 때"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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