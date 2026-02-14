from .health_controller import router as health_router
from .ai_controller import router as ai_router
# from .chat_controller import router as chat_router  # DynamoDB 의존 - Communication 서비스로 분리 예정

# 모든 라우터를 리스트로 묶어서 관리
# (router, prefix, tags) 순서로 정의
all_routers = [
    (health_router, "/health", "Health"),
    (ai_router, "/ai", "AI Service"),  # prefix 추가
    # (chat_router, "/chat", "Chat")  # DynamoDB 없이 테스트 시 비활성화
]