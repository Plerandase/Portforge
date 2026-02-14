from enum import Enum
from fastapi import status

class ErrorCode(Enum):
    # ===== 공통 에러 =====
    SUCCESS = ("COMMON_000", "정상 처리되었습니다.", status.HTTP_200_OK)
    INVALID_INPUT = ("COMMON_001", "입력값이 유효하지 않습니다.", status.HTTP_400_BAD_REQUEST)
    UNAUTHORIZED = ("COMMON_002", "인증에 실패했습니다.", status.HTTP_401_UNAUTHORIZED)
    FORBIDDEN = ("COMMON_003", "권한이 없습니다.", status.HTTP_403_FORBIDDEN)
    NOT_FOUND = ("COMMON_004", "리소스를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    INTERNAL_SERVER_ERROR = ("COMMON_999", "서버 내부 오류가 발생했습니다.", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ===== 인증 에러 (AUTH_1xx) =====
    AUTH_EMAIL_DUPLICATE = ("AUTH_101", "이미 가입된 이메일입니다.", status.HTTP_409_CONFLICT)
    AUTH_NICKNAME_DUPLICATE = ("AUTH_102", "이미 사용 중인 닉네임입니다.", status.HTTP_409_CONFLICT)
    AUTH_COGNITO_USER_EXISTS = ("AUTH_103", "이미 Cognito에 등록된 계정입니다.", status.HTTP_409_CONFLICT)
    AUTH_INVALID_PASSWORD_FORMAT = ("AUTH_104", "비밀번호 형식이 올바르지 않습니다. (8자 이상, 대소문자, 숫자, 특수문자 포함)", status.HTTP_400_BAD_REQUEST)
    AUTH_COGNITO_ERROR = ("AUTH_105", "AWS 인증 서비스 오류가 발생했습니다.", status.HTTP_503_SERVICE_UNAVAILABLE)
    
    # ===== 로그인 에러 (AUTH_2xx) =====
    AUTH_INVALID_CREDENTIALS = ("AUTH_201", "이메일 또는 비밀번호가 잘못되었습니다.", status.HTTP_401_UNAUTHORIZED)
    AUTH_EMAIL_NOT_VERIFIED = ("AUTH_202", "이메일 인증이 완료되지 않았습니다. 메일함을 확인해주세요.", status.HTTP_403_FORBIDDEN)
    AUTH_USER_NOT_FOUND = ("AUTH_203", "가입되지 않은 이메일입니다.", status.HTTP_404_NOT_FOUND)
    AUTH_LOGIN_FAILED = ("AUTH_204", "로그인에 실패했습니다.", status.HTTP_400_BAD_REQUEST)
    
    # ===== 이메일 인증 에러 (AUTH_3xx) =====
    AUTH_VERIFICATION_CODE_EXPIRED = ("AUTH_301", "인증 코드가 만료되었습니다. 새 코드를 요청해주세요.", status.HTTP_400_BAD_REQUEST)
    AUTH_VERIFICATION_CODE_MISMATCH = ("AUTH_302", "인증 코드가 일치하지 않습니다.", status.HTTP_400_BAD_REQUEST)
    AUTH_ALREADY_VERIFIED = ("AUTH_303", "이미 인증이 완료된 계정입니다.", status.HTTP_400_BAD_REQUEST)
    AUTH_RESEND_FAILED = ("AUTH_304", "인증 코드 재발송에 실패했습니다.", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ===== 사용자 에러 (USER_4xx) =====
    USER_NOT_FOUND = ("USER_401", "사용자를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    USER_PROFILE_UPDATE_FAILED = ("USER_402", "프로필 수정에 실패했습니다.", status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # ===== 비밀번호 에러 (AUTH_5xx) =====
    AUTH_PASSWORD_CHANGE_FAILED = ("AUTH_501", "비밀번호 변경에 실패했습니다.", status.HTTP_400_BAD_REQUEST)
    AUTH_PASSWORD_RESET_FAILED = ("AUTH_502", "비밀번호 재설정에 실패했습니다.", status.HTTP_400_BAD_REQUEST)
    
    # ===== 토큰 에러 (AUTH_6xx) =====
    AUTH_TOKEN_EXPIRED = ("AUTH_601", "토큰이 만료되었습니다. 다시 로그인해주세요.", status.HTTP_401_UNAUTHORIZED)
    AUTH_TOKEN_INVALID = ("AUTH_602", "유효하지 않은 토큰입니다.", status.HTTP_401_UNAUTHORIZED)

    def __init__(self, biz_code, default_message, http_status):
        self.biz_code = biz_code
        self.default_message = default_message
        self.http_status = http_status


class BusinessException(Exception):
    """팀원들이 raise BusinessException(...)으로 던질 예외 객체"""
    def __init__(self, error_code: ErrorCode, detail: str = None):
        self.error_code = error_code
        self.message = detail or error_code.default_message
        super().__init__(self.message)