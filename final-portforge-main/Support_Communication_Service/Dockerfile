FROM python:3.13.7-slim
WORKDIR /app

# 시스템 패키지 설치 (MySQL 클라이언트 필요)
RUN apt-get update && apt-get install -y default-libmysqlclient-dev gcc && rm -rf /var/lib/apt/lists/*

RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --without dev --no-root
COPY . .
EXPOSE 8004

# 시작 시 마이그레이션 실행 후 앱 시작
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8004