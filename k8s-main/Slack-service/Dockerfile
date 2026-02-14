# =================================================================
# Slack Monitoring Bot Dockerfile - Socket Mode
# =================================================================
FROM python:3.13-slim

WORKDIR /app

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY bot.py .

# 비root 사용자 생성
RUN groupadd -r slackbot && useradd -r -g slackbot slackbot
RUN chown -R slackbot:slackbot /app
USER slackbot

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 헬스체크 (프로세스 체크)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python bot.py" || exit 1

# 봇 실행
CMD ["python", "bot.py"]