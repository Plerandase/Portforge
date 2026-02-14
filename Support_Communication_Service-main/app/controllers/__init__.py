from .health_controller import router as health_router
from .notifications_controller import router as notifications_router
from .events_controller import router as events_router
from .admin_controller import router as admin_router
from .content_controller import router as content_router
from .chat_controller import router as chat_router

# 모든 라우터를 튜플로 묶어 관리합니다.
# (router, prefix, tags) 순서로 정의
# 
# ⚠️ 주의: auth, users, projects, teams, tests는 각각의 전용 서비스에서 처리됩니다.
# Support Service는 채팅, 알림, 공지사항, 이벤트 관리만 담당합니다.
all_routers = [
    (health_router, "/health", "Health"),
    (notifications_router, "/notifications", "Notifications"),
    (events_router, "/events", "Events"),
    (admin_router, "/admin", "Admin"),
    (content_router, "", "Content"),  # /notices, /banners 등
    (chat_router, "", "Chat"),        # /chat, /ws 등
]
