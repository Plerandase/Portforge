FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

# 헬스체크 및 서비스 포트
EXPOSE 8005
# workers=1로 설정하여 백그라운드 스케줄러가 정상 동작하도록 함
# (멀티 워커 모드에서는 threading 기반 스케줄러가 제대로 동작하지 않음)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "1"]