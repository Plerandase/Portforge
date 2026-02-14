from enum import Enum
from fastapi import status

class ErrorCode(Enum):
    # 어떤 프로젝트든 공통으로 필요한 에러만 정의
    SUCCESS = ("COMMON_000", "정상 처리되었습니다.", status.HTTP_200_OK)
    INVALID_INPUT = ("COMMON_001", "입력값이 유효하지 않습니다.", status.HTTP_400_BAD_REQUEST)
    UNAUTHORIZED = ("COMMON_002", "인증에 실패했습니다.", status.HTTP_401_UNAUTHORIZED)
    INTERNAL_SERVER_ERROR = ("COMMON_999", "서버 내부 오류가 발생했습니다.", status.HTTP_500_INTERNAL_SERVER_ERROR)

    def __init__(self, biz_code, default_message, http_status):
        self.biz_code = biz_code
        self.default_message = default_message
        self.http_status = http_status

class BusinessException(Exception):
    """팀원들이 raise BusinessException(...)으로 던질 예외 객체"""
    def __init__(self, error_code: ErrorCode, detail: str = None or "Unknown error"):
        self.error_code = error_code
        self.message = detail or error_code.default_message