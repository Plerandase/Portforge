# 1. 파이썬 3.13 슬림 버전 사용
FROM python:3.13-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 시스템 의존성 설치 (MySQL/PostgreSQL 빌드 도구 포함)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Poetry 설치
RUN pip install poetry

# 5. 의존성 파일 복사 및 설치
# (캐시 활용을 위해 소스 코드보다 먼저 복사)
COPY pyproject.toml poetry.lock ./

# 6. 가상환경 생성 방지 (도커 컨테이너 자체가 격리된 환경이므로)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# 7. 전체 소스 코드 복사
COPY . .

# 8. 포트 개방
EXPOSE 8000

# 9. 캐시 무효화를 위한 ARG
ARG CACHEBUST=1

# 10. 서버 실행 (app 폴더 안의 main.py 실행)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]