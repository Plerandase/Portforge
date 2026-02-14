from .health_controller import router as health_router
# from .project_controller import router as project_router  # Temporarily disabled due to model conflicts
from .project_recruitment_controller import router as project_recruitment_router
from .application_controller import router as application_router
# 팀원이 새 컨트롤러를 만들면 여기에 한 줄만 추가하도록 가이드

# 모든 라우터를 리스트로 묶어서 관리
# (router, prefix, tags) 순서로 정의
all_routers = [
    (health_router, "/health", "Health"),
    # (project_router, "", "Projects"),  # Temporarily disabled
    (project_recruitment_router, "", "Recruitment"),  # prefix is already set in router
    (application_router, "", "Applications")  # 지원서 관리 API
]