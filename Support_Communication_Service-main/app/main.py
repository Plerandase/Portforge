from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import BusinessException
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.middleware import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.controllers import all_routers
import logging
import sys

# 로깅 설정: INFO 레벨로 설정하고 stdout으로 출력
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI(
    title="Portforge Support & Communication Service",
    description="고객지원, 채팅, 공지사항, 알림 서비스",
    version="1.0.0"
)

# 1. 로그 미들웨어 등록
app.add_middleware(LoggingMiddleware)

# 1-1. 개발 편의를 위한 CORS 허용 (필요에 따라 도메인 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 프로메테우스 메트릭 설정 (자동으로 /metrics 엔드포인트 생성)
Instrumentator().instrument(app).expose(app)

# 3. 반복문으로 새 컨트롤러(api) 자동 등록
for router, prefix, tag in all_routers:
    app.include_router(router, prefix=prefix, tags=[tag])

# 전역 예외 핸들러: 한 번 등록하면 팀원들은 신경 안 써도 됨
@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.error_code.http_status,
        content={
            "success": False,
            "code": exc.error_code.biz_code,
            "message": exc.message,
            "data": None
        }
    )

@app.get("/")
async def root():
    return {"message": "Support & Communication Service is running", "service": "support-service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "support-service"}
