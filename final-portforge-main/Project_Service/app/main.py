from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import BusinessException
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.middleware import LoggingMiddleware
from app.controllers import all_routers
# from app.controllers.project_controller import router as project_router  # Temporarily disabled

# MSA API 라우터 추가
from app.api.projects import router as projects_router
from app.api.enriched_projects import router as enriched_router
from app.api.project_crud import router as project_crud_router
from app.api.applications import router as applications_router

app = FastAPI(
    title="Portforge Project Collaboration Platform API",
    description="""
    ## 프로젝트 협업 플랫폼 API

    이 API는 개발자들이 프로젝트를 생성하고, 팀원을 모집하며, 협업할 수 있는 플랫폼을 제공합니다.

    ### 주요 기능:
    - **프로젝트 관리**: 프로젝트 생성, 수정, 삭제, 조회
    - **팀원 모집**: 포지션별 팀원 모집 및 지원서 관리
    - **AI 역량 테스트**: 지원자의 기술 역량 평가
    - **실시간 협업**: 팀 채팅 및 회의록 관리

    ### API 버전: v1.0
    """,
    version="1.0.0",
    contact={
        "name": "Portforge Team",
        "email": "support@portforge.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# 1. CORS 미들웨어 등록 (React 프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
    allow_credentials=False,  # credentials를 False로 설정 (allow_origins=["*"]와 함께 사용 시 필요)
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. 로그 미들웨어 등록
app.add_middleware(LoggingMiddleware)

# 3. 프로메테우스 메트릭 설정 (자동으로 /metrics 엔드포인트 생성)
Instrumentator().instrument(app).expose(app)

# 4. 반복문으로 새 컨트롤러(api) 자동 등록
for router, prefix, tag in all_routers:
    app.include_router(router, prefix=prefix, tags=[tag])

# 5. MSA API 라우터 등록
app.include_router(projects_router)  # /projects 경로 (기존 조회용)
app.include_router(enriched_router)  # /enriched 경로
app.include_router(project_crud_router)  # /projects 경로 (CRUD용)
app.include_router(applications_router)  # /projects/{id}/applications 경로

# 6. Explicitly include project router to ensure it's always available (temporarily disabled)
# app.include_router(project_router, tags=["Projects"])

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

# Validation Error 핸들러 추가
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ Validation Error: {exc}")
    print(f"❌ Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "요청 데이터 유효성 검사 실패",
            "errors": exc.errors(),
            "detail": str(exc)
        }
    )

@app.get("/")
async def root():
    return {"message": "Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working"}