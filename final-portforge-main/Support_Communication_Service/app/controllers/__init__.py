from .health_controller import router as health_router
from .auth_controller import router as auth_router
from .users_controller import router as users_router
from .notifications_controller import router as notifications_router
from .projects_controller import router as projects_router
from .teams_controller import router as teams_router
from .tests_controller import router as tests_router
from .events_controller import router as events_router
from .admin_controller import router as admin_router
from .content_controller import router as content_router
from .chat_controller import router as chat_router

# 모든 라우터를 튜플로 묶어 관리합니다.
# (router, prefix, tags) 순서로 정의
all_routers = [
    (health_router, "/health", "Health"),
    (auth_router, "/auth", "Auth"),
    (users_router, "/users", "Users"),
    (notifications_router, "/notifications", "Notifications"),
    (projects_router, "/projects", "Projects"),
    (teams_router, "/teams", "Teams"),
    (tests_router, "/test", "Tests"),
    (events_router, "/events", "Events"),
    (admin_router, "/admin", "Admin"),
    (content_router, "", "Content"),
    (chat_router, "", "Chat"),
]
