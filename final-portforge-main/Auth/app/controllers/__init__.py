from .health_controller import router as health_router
# 팀원이 새 컨트롤러를 만들면 여기에 한 줄만 추가하도록 가이드

# 모든 라우터를 리스트로 묶어서 관리
# (router, prefix, tags) 순서로 정의
all_routers = [
    (health_router, "/health", "Health")
]