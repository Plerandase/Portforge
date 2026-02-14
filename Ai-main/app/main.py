from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import BusinessException
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.middleware import LoggingMiddleware
from app.controllers import all_routers

# MSA API 라우터 추가
from app.api.ai_data import router as ai_data_router

app = FastAPI(
    title="Portforge AI Service",
    description="AI 기반 테스트, 회의록 생성, 포트폴리오 서비스",
    version="1.0.0"
)

# 1. CORS 미들웨어 등록 (프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 로그 미들웨어 등록
app.add_middleware(LoggingMiddleware)

# 2. 프로메테우스 메트릭 설정 (자동으로 /metrics 엔드포인트 생성)
Instrumentator().instrument(app).expose(app)

# 3. 반복문으로 새 컨트롤러(api) 자동 등록
for router, prefix, tag in all_routers:
    app.include_router(router, prefix=prefix, tags=[tag])

# 4. MSA API 라우터 등록
app.include_router(ai_data_router, prefix="/ai")  # /ai 경로

from app.core.database import engine
from app.models import ai_model

@app.on_event("startup")
async def startup_event():
    print("Initializing Database Tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(ai_model.Base.metadata.create_all)
        print("Database Tables Initialized Successfully.")
    except Exception as e:
        print(f"CRITICAL DATABASE ERROR: {e}")
        # 여기서 에러가 나면 DB 연결 정보(.env)가 틀렸거나 DB 서버가 죽은 것입니다.

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

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    error_detail = "".join(traceback.format_exception(None, exc, exc.__traceback__))
    print(f"CRITICAL ERROR: {error_detail}")  # 콘솔에 에러 출력
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal Server Error: {str(exc)}"
        }
    )

@app.get("/")
async def root():
    return {"message": "AI Service is running", "service": "ai-service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-service"}