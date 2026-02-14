import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

# 기본 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_logger")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 요청마다 고유 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # 2. 다음 단계(컨트롤러)로 요청 전달
        response = await call_next(request)
        
        # 3. 처리 시간 계산 및 로깅
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        
        logger.info(
            f"ID: {request_id} | Method: {request.method} | Path: {request.url.path} "
            f"| Status: {response.status_code} | Duration: {process_time:.4f}s"
        )
        
        return response