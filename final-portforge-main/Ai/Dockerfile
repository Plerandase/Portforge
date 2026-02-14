# =================================================================
# AI Service Dockerfile
# =================================================================
# 빌더 스테이지 시작: 경량 Python 3.13 이미지를 사용합니다.
FROM python:3.13-slim AS builder

# 작업 디렉토리를 /app으로 설정합니다.
WORKDIR /app

# Poetry 1.8.0을 설치합니다.
RUN pip install poetry==2.2.1

# pyproject.toml 및 poetry.lock 파일을 현재 디렉토리로 복사합니다.
COPY pyproject.toml poetry.lock ./

# 가상 환경 생성을 비활성화하고, 개발 종속성 없이 메인 종속성만 설치합니다.
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# =================================================================
# Production Stage
# =================================================================
# 프로덕션 스테이지 시작: 경량 Python 3.13 이미지를 사용합니다.
FROM python:3.13-slim

# 작업 디렉토리를 /app으로 설정합니다.
WORKDIR /app

# 'appgroup' 그룹과 'appuser' 사용자를 생성합니다.
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 빌더 스테이지에서 설치된 Python 패키지를 복사합니다.
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
# 빌더 스테이지에서 설치된 실행 파일을 복사합니다.
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드를 복사합니다.
COPY app ./app

# /app 디렉토리의 소유권을 appuser:appgroup으로 변경합니다.
RUN chown -R appuser:appgroup /app

# 컨테이너 실행 시 사용할 사용자를 appuser로 설정합니다.
USER appuser

# 환경 변수를 설정합니다.
# PYTHONUNBUFFERED=1: Python 출력을 버퍼링하지 않고 즉시 출력합니다.
# PYTHONDONTWRITEBYTECODE=1: Python이 .pyc 파일을 생성하지 않도록 합니다.
# PORT=8003: 애플리케이션이 수신할 포트를 설정합니다.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8003

# 8003 포트를 외부에 노출합니다.
EXPOSE 8003

# 컨테이너의 상태를 확인하는 헬스체크를 설정합니다.
# 30초 간격으로, 10초 타임아웃, 시작 후 5초 대기, 3회 재시도합니다.
# http://localhost:8003/health 엔드포인트에 요청을 보내 성공 여부를 확인합니다.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

# 컨테이너가 시작될 때 실행될 기본 명령을 설정합니다.
# Uvicorn을 사용하여 app.main 모듈의 'app' 객체를 실행하고, 모든 IP 주소에서 8003 포트로 수신합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
