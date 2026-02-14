import os
import uuid
import aioboto3
import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_db, get_current_user # 의존성 임포트 확인
from app.models.user import User, UserStack
from app.models.enums import UserRole, StackCategory, TechStack
from app.core.config import settings  # [추가] 중앙 설정 import
from app.core.exceptions import BusinessException, ErrorCode  # [추가] 비즈니스 예외
from app.schemas.user_update import UserUpdate # [추가] UserUpdate 스키마
from app.schemas.user import (
    UserSimple,
    UserCreate, 
    UserResponse, 
    NicknameCheckResponse, 
    UserLogin, 
    LoginResponse, 
    EmailVerification, 
    UserSimple, 
    PasswordChange, 
    ForgotPasswordRequest, 
    ConfirmForgotPassword,
    DeleteAccountRequest,
    DeleteAccountResponse
)

# [수정 1] 명세서에 /auth와 /users가 섞여 있으므로, 고정 prefix를 제거하고 태그만 유지합니다.
router = APIRouter(tags=["auth"])

# 로거 설정 
logger = logging.getLogger("api_logger")

# =================================================================
# 1. 회원가입 (Spec: POST /auth/join) - Cognito sub 동기화 버전
# =================================================================
@router.post("/join", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    # A. 로컬 DB 중복 검사
    if db.scalar(select(User).where(User.email == user_in.email)):
        raise BusinessException(ErrorCode.AUTH_EMAIL_DUPLICATE)
    if db.scalar(select(User).where(User.nickname == user_in.nickname)):
        raise BusinessException(ErrorCode.AUTH_NICKNAME_DUPLICATE)

    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        # B. AWS Cognito 회원가입
        try:
            response = await client.sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=user_in.email,
                Password=user_in.password,
                UserAttributes=[
                    {"Name": "email", "Value": user_in.email},
                    {"Name": "nickname", "Value": user_in.nickname}
                ]
            )
            cognito_sub = response["UserSub"]
            logger.info(f"Cognito Signup Success: {user_in.email} (sub: {cognito_sub})")
            
        except client.exceptions.UsernameExistsException:
            # Cognito에는 있는데 DB에는 없는 경우 (데이터 불일치) -> DB에 저장 시도하거나 에러 처리
            # 여기서는 명확히 에러로 처리
            raise BusinessException(ErrorCode.AUTH_COGNITO_USER_EXISTS)
        except client.exceptions.InvalidPasswordException:
            raise BusinessException(ErrorCode.AUTH_INVALID_PASSWORD_FORMAT)
        except Exception as e:
            logger.error(f"Cognito Signup Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_COGNITO_ERROR, f"Cognito 오류: {str(e)}")

        # C. 로컬 DB 저장 (실패 시 Cognito 롤백)
        try:
            new_user = User(
                user_id=cognito_sub,
                email=user_in.email,
                nickname=user_in.nickname,
                role=UserRole.USER,
                test_count=5  # ERD 기본값
            )
            db.add(new_user)
            
            # [추가] 기술 스택 저장
            for stack in user_in.stacks:
                new_stack = UserStack(
                    user_id=cognito_sub,
                    position_type=stack.position_type,
                    stack_name=stack.stack_name
                )
                db.add(new_stack)

            db.commit()
            db.refresh(new_user)
            logger.info(f"DB Save Success: {user_in.email}")
            return new_user

        except Exception as db_error:
            db.rollback()
            logger.error(f"DB Save Error: {str(db_error)} - Rolling back Cognito user...")
            
            # [롤백] Cognito 계정 삭제
            try:
                # admin_delete_user를 사용하려면 AWS Developer Credential이 필요함
                # 일반 sign_up 클라이언트로는 삭제 권한이 없을 수 있으나, 
                # settings.AWS_ACCESS_KEY_ID 등이 설정되어 있다면 가능
                await client.admin_delete_user(
                    UserPoolId=settings.EFFECTIVE_USER_POOL_ID,
                    Username=user_in.email
                )
                logger.info(f"Cognito Rollback Success: {user_in.email}")
            except Exception as rollback_error:
                logger.critical(f"CRITICAL: Cognito Rollback Failed for {user_in.email}: {str(rollback_error)}")
            
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "회원가입 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")



# =================================================================
# 2. 닉네임 중복 검증 (Spec: GET /auth/validate_nickname)
# =================================================================
@router.get("/validate_nickname", status_code=status.HTTP_200_OK)
def check_nickname(nickname: str, db: Session = Depends(get_db)):
    # 1. 유효성 검사 (길이)
    if len(nickname) < 2 or len(nickname) > 10:
        return {"available": False, "message": "닉네임은 2자 이상 10자 이하여야 합니다."}
    
    # 2. DB 중복 확인
    exists_user = db.query(User).filter(User.nickname == nickname).first()
    exists = exists_user is not None

    return {
        "available": not exists,
        "message": "이미 사용 중인 닉네임입니다." if exists else "사용 가능한 닉네임입니다."
    }


# =================================================================
# 3. 로그인 (Spec: POST /auth/login)
# =================================================================
@router.post("/login", response_model=LoginResponse)
async def login(user_in: UserLogin, db: Session = Depends(get_db)):
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            response = await client.initiate_auth(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": user_in.email,
                    "PASSWORD": user_in.password,
                },
            )
            auth_result = response["AuthenticationResult"]
        except client.exceptions.NotAuthorizedException:
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS)
        except client.exceptions.UserNotConfirmedException:
            raise BusinessException(ErrorCode.AUTH_EMAIL_NOT_VERIFIED)
        except client.exceptions.UserNotFoundException:
            raise BusinessException(ErrorCode.AUTH_USER_NOT_FOUND)
        except Exception as e:
            logger.error(f"Login Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_LOGIN_FAILED, f"로그인 실패: {str(e)}")


    user = db.scalar(select(User).where(User.email == user_in.email))
    if not user:
        raise BusinessException(ErrorCode.USER_NOT_FOUND)

    return {
        "access_token": auth_result["AccessToken"],
        "id_token": auth_result.get("IdToken"),  # 세션 유지를 위해 ID Token 필수 포함
        "token_type": auth_result["TokenType"],
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "myStacks": user.myStacks,  # 프로퍼티로 정의됨
            "test_count": user.test_count,
            "liked_project_ids": user.liked_project_ids or []
        }
    }


# =================================================================
# 4. 로그아웃 (Spec: POST /auth/logout) - [신규 추가]
# =================================================================
@router.post("/logout")
async def logout(authorization: str = Header(None)):
    # JWT 방식(Stateless)이라 서버에서 강제 만료는 어렵지만,
    # 명세서 준수를 위해 성공 응답을 반환합니다. (추후 블랙리스트 구현 가능)
    if not authorization:
        raise HTTPException(status_code=401, detail="토큰이 필요합니다.")
    return {"message": "로그아웃 처리되었습니다."}


# =================================================================
# 5. 내 정보 조회 (Spec: GET /users/me) - [최신화: deps 사용]
# =================================================================
@router.get("/me", response_model=UserSimple)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    [세션 유지용 API]
    deps.py의 get_current_user가 토큰을 검사하고, 
    DB에서 찾아낸 유저 정보를 그대로 반환합니다.
    """
    return current_user

# =================================================================
# [추가] 내 정보 수정 (Spec: PUT /users/me)
# =================================================================
def get_stack_category(stack_name: str) -> StackCategory:
    """스택 이름으로 카테고리 추론"""
    if stack_name in ["React", "Vue", "Nextjs", "Svelte", "Angular", "TypeScript", "JavaScript", "TailwindCSS", "StyledComponents", "Redux", "Recoil", "Vite", "Webpack"]:
        return StackCategory.FRONTEND
    if stack_name in ["Java", "Spring", "Nodejs", "Nestjs", "Go", "Python", "Django", "Flask", "Express", "php", "Laravel", "RubyonRails", "CSharp", "DotNET"]:
        return StackCategory.BACKEND
    if stack_name in ["MySQL", "PostgreSQL", "MongoDB", "Redis", "Oracle", "SQLite", "MariaDB", "Cassandra", "DynamoDB", "FirebaseFirestore", "Prisma"]:
        return StackCategory.DB
    if stack_name in ["AWS", "Docker", "Kubernetes", "GCP", "Azure", "Terraform", "Jenkins", "GithubActions", "Nginx", "Linux", "Vercel", "Netlify"]:
        return StackCategory.INFRA
    if stack_name in ["Figma", "AdobeXD", "Sketch", "Canva", "Photoshop", "Illustrator", "Blender", "UIUX_Design", "Branding"]:
        return StackCategory.DESIGN
    return StackCategory.ETC

@router.put("/me")
def update_user_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 닉네임 수정
    if user_data.name:
        current_user.nickname = user_data.name
    
    # 2. 프로필 이미지 수정
    if user_data.profile_image_url is not None:
        current_user.profile_image_url = user_data.profile_image_url
    
    # 3. 기술 스택 수정 (전체 삭제 후 재생성)
    if user_data.myStacks is not None:
        # 기존 스택 삭제
        db.query(UserStack).filter(UserStack.user_id == current_user.user_id).delete()
        
        # 새 스택 추가
        for s_name in user_data.myStacks:
            try:
                # Enum 검증 (대소문자 구분 없이 매칭 시도 가능하지만, 일단 정확 매칭 시도)
                # 프론트엔드가 TechStack Enum 값(문자열)을 그대로 보내준다고 가정
                tech_stack = TechStack(s_name)
                category = get_stack_category(s_name)
                
                new_stack = UserStack(
                    user_id=current_user.user_id,
                    position_type=category,
                    stack_name=tech_stack
                )
                db.add(new_stack)
            except ValueError:
                # TechStack Enum에 없는 값은 무시하거나 로그 남김
                logger.warning(f"지원하지 않는 기술 스택 무시됨: {s_name}")
                continue
    
    try:
        db.commit()
        db.refresh(current_user)
        return {"message": "프로필이 업데이트되었습니다."}
    except Exception as e:
        db.rollback()
        logger.error(f"프로필 업데이트 실패: {str(e)}")
        raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "프로필 저장 중 오류가 발생했습니다.")

# =================================================================
# [추가] 프로젝트 좋아요 토글 (POST /users/me/likes/{project_id})
# =================================================================
@router.post("/me/likes/{project_id}")
def toggle_like_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """프로젝트 좋아요/취소 토글"""
    liked_ids = current_user.liked_project_ids or []
    
    if project_id in liked_ids:
        # 이미 좋아요한 경우 -> 취소
        liked_ids.remove(project_id)
        action = "removed"
    else:
        # 좋아요 추가
        liked_ids.append(project_id)
        action = "added"
    
    current_user.liked_project_ids = liked_ids
    db.commit()
    
    return {
        "project_id": project_id,
        "action": action,
        "liked_project_ids": liked_ids
    }

# =================================================================
# 6. 비밀번호 변경 (Spec: PUT /users/{user_id}/password)
# [변경] POST -> PUT, URL 변경. {user_id}는 보안상 토큰 본인인지 체크 필요하나, 
# 일단 구현 편의를 위해 토큰만으로 처리하도록 연결합니다.
# =================================================================
@router.put("/{user_id}/password")
async def change_password(user_id: str, data: PasswordChange, authorization: str = Header(None)):
    # user_id 파라미터가 있지만, 실제로는 보안을 위해 AccessToken을 사용해 Cognito에 요청합니다.
    # (추후 user_id와 토큰 소유자가 일치하는지 검증 로직 추가 권장)
    
    if not authorization:
        raise BusinessException(ErrorCode.UNAUTHORIZED, "로그인이 필요합니다.")
    token = authorization.replace("Bearer ", "")
    
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            await client.change_password(
                PreviousPassword=data.old_password,
                ProposedPassword=data.new_password,
                AccessToken=token
            )
            return {"message": "비밀번호가 변경되었습니다."}
        except client.exceptions.NotAuthorizedException:
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "현재 비밀번호가 일치하지 않습니다.")
        except client.exceptions.InvalidPasswordException:
             raise BusinessException(ErrorCode.AUTH_INVALID_PASSWORD_FORMAT)
        except Exception as e:
            logger.error(f"PW Change Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_PASSWORD_CHANGE_FAILED, f"비밀번호 변경 중 오류 발생: {str(e)}")


# =================================================================
# [기타] 명세서 미포함이지만 앱 작동에 필수적인 API (주소는 /auth로 통일)
# =================================================================

# 이메일 인증 코드 확인


# 비밀번호 찾기 (요청)
@router.post("/forgot-password")
async def forgot_password_request(data: ForgotPasswordRequest):
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            await client.forgot_password(ClientId=settings.COGNITO_APP_CLIENT_ID, Username=data.email)
            return {"message": "인증 코드가 이메일로 발송되었습니다."}
        except client.exceptions.UserNotFoundException:
             raise BusinessException(ErrorCode.AUTH_USER_NOT_FOUND)
        except Exception as e:
            logger.error(f"Forgot Password Request Error: {str(e)}")
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, f"오류가 발생했습니다: {str(e)}")

# 비밀번호 찾기 (재설정)
@router.post("/confirm-forgot-password")
async def confirm_forgot_password(data: ConfirmForgotPassword):
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            await client.confirm_forgot_password(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=data.email,
                ConfirmationCode=data.code,
                Password=data.new_password
            )
            return {"message": "비밀번호가 성공적으로 재설정되었습니다."}
        except client.exceptions.CodeMismatchException:
             raise BusinessException(ErrorCode.AUTH_VERIFICATION_CODE_MISMATCH)
        except client.exceptions.ExpiredCodeException:
             raise BusinessException(ErrorCode.AUTH_VERIFICATION_CODE_EXPIRED)
        except Exception as e:
            logger.error(f"Confirm Password Reset Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_PASSWORD_RESET_FAILED, f"재설정 실패: {str(e)}")

# [소셜 로그인] 구글/카카오 등이 준 Code를 토큰으로 교환
@router.post("/social/callback")
async def social_callback(data: dict, db: Session = Depends(get_db)):
    code = data.get("code")
    if not code:
        raise BusinessException(ErrorCode.INVALID_INPUT_VALUE, "인증 코드가 없습니다.")

    # 1. 환경 변수 가져오기 및 검증 (settings 사용)
    cognito_domain = settings.COGNITO_DOMAIN
    redirect_uri = settings.REDIRECT_URI
    client_id = settings.COGNITO_APP_CLIENT_ID
    
    # 필수 환경변수 검증
    if not cognito_domain or not redirect_uri or not client_id:
        logger.error(f"환경변수 누락: domain={bool(cognito_domain)}, redirect={bool(redirect_uri)}, clean_id={bool(client_id)}")
        raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "소셜 로그인 설정 오류")

    # 2. Cognito 토큰 엔드포인트 호출
    cognito_region = os.getenv("COGNITO_REGION", "ap-northeast-2")
    token_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'redirect_uri': redirect_uri
    }
    
    logger.info(f"토큰 교환 요청: URL={token_url}, client_id={client_id}, redirect_uri={redirect_uri}")
    
    # 비밀번호(Secret) 없이 요청 전송 (Public Client)
    async with httpx.AsyncClient() as http_client:
        try:
            resp = await http_client.post(token_url, data=payload, headers=headers)
            
            logger.info(f"토큰 교환 응답: status={resp.status_code}")
            
            if resp.status_code != 200:
                error_detail = resp.text
                logger.error(f"토큰 교환 실패: {error_detail}")
                raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, f"토큰 교환 실패: {error_detail}")
            
            tokens = resp.json()
            access_token = tokens.get("access_token")
            
            if not access_token:
                logger.error(f"액세스 토큰이 응답에 없습니다: {tokens}")
                raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "액세스 토큰을 받지 못했습니다.")

            # 3. 토큰으로 사용자 정보 가져오기
            user_info_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/userInfo"
            user_info_headers = {"Authorization": f"Bearer {access_token}"}
            
            logger.info(f"사용자 정보 요청: URL={user_info_url}")
            
            user_info_resp = await http_client.get(user_info_url, headers=user_info_headers)
            
            logger.info(f"사용자 정보 응답: status={user_info_resp.status_code}")
            
            if user_info_resp.status_code != 200:
                error_detail = user_info_resp.text
                logger.error(f"사용자 정보 조회 실패: {error_detail}")
                raise BusinessException(ErrorCode.AUTH_USER_NOT_FOUND, f"사용자 정보 조회 실패: {error_detail}")
            
            user_info = user_info_resp.json()
            logger.info(f"사용자 정보 수신 성공: {user_info}")
            
        except httpx.RequestError as e:
            logger.error(f"HTTP 요청 오류: {str(e)}")
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, f"네트워크 오류: {str(e)}")
        except Exception as e:
            if isinstance(e, BusinessException):
                raise e
            logger.error(f"예상치 못한 오류: {str(e)}")
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, f"소셜 로그인 처리 중 오류: {str(e)}")
        
    # 4. 로컬 DB 동기화
    email = user_info.get("email")
    if not email:
        logger.error(f"사용자 정보에 이메일이 없습니다: {user_info}")
        raise HTTPException(status_code=400, detail="사용자 이메일 정보를 받을 수 없습니다.")
    
    # 닉네임이 없으면 이메일 앞부분 사용
    nickname = user_info.get("nickname") or user_info.get("name") or email.split("@")[0]
    
    try:
        user = db.scalar(select(User).where(User.email == email))
        
        if not user:
            # 닉네임 중복 방지 (기존 유저와 겹치면 랜덤 숫자 추가)
            if db.scalar(select(User).where(User.nickname == nickname)):
                import random
                nickname = f"{nickname}_{random.randint(1000, 9999)}"

            user = User(
                user_id=str(uuid.uuid4()),
                email=email, 
                nickname=nickname, 
                role=UserRole.USER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"새 사용자 생성: {email}")
        else:
            logger.info(f"기존 사용자 로그인: {email}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 오류: {str(e)}")
        raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, f"사용자 정보 저장 중 오류: {str(e)}")
    
    return {
        # social_callback에서는 tokens라는 변수에 데이터가 담겨 있습니다.
        "access_token": tokens.get("access_token") or tokens.get("AccessToken"),
        "id_token": tokens.get("id_token") or tokens.get("IdToken"), # 이메일 정보 포함 토큰
        "token_type": tokens.get("token_type") or tokens.get("TokenType"),
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "myStacks": user.myStacks  # 프로퍼티로 정의됨
        }
    }

# =================================================================
# [디버깅용] 소셜 로그인 설정 확인 API
# =================================================================
@router.get("/social/config")
async def check_social_config():
    """
    소셜 로그인 설정 상태를 확인하는 디버깅용 API
    민감한 정보는 마스킹하여 반환
    """
    cognito_domain = settings.COGNITO_DOMAIN
    redirect_uri = settings.REDIRECT_URI
    client_id = settings.COGNITO_APP_CLIENT_ID
    
    # 민감한 정보 마스킹
    masked_client_id = f"{client_id[:4]}***{client_id[-4:]}" if client_id else None
    
    return {
        "cognito_domain": cognito_domain,
        "redirect_uri": redirect_uri,
        "client_id_masked": masked_client_id,
        "config_status": {
            "cognito_domain_set": bool(cognito_domain),
            "redirect_uri_set": bool(redirect_uri),
            "client_id_set": bool(client_id)
        }
    }

# =================================================================
# 소셜 로그인 URL 생성 API
# =================================================================
@router.get("/social/login-url")
async def get_social_login_url(provider: str):
    """
    소셜 로그인 URL을 생성하여 반환합니다.
    프론트엔드는 이 URL로 리다이렉트하여 소셜 로그인을 진행합니다.
    """
    cognito_domain = settings.COGNITO_DOMAIN
    client_id = settings.COGNITO_APP_CLIENT_ID
    redirect_uri = settings.REDIRECT_URI
    
    if not cognito_domain or not client_id:
        raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "소셜 로그인 설정이 완료되지 않았습니다.")
    
    # 프로바이더 매핑 (Cognito Identity Provider 이름)
    provider_map = {
        "Google": "Google",
        "Kakao": "Kakao",
        "Naver": "Naver",
        "GitHub": "GitHub"
    }
    
    identity_provider = provider_map.get(provider)
    if not identity_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 소셜 로그인 프로바이더입니다: {provider}"
        )
    
    # Cognito OAuth2 인증 URL 생성
    from urllib.parse import urlencode
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "identity_provider": identity_provider,
        "scope": "openid email profile",
        "prompt": "select_account" # 계정 선택 강제 (자동 로그인 방지)
    }
    
    # Cognito OAuth2 인증 URL 생성 (Full URL 필요)
    cognito_region = os.getenv("COGNITO_REGION", "ap-northeast-2")
    cognito_base_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com"
    auth_url = f"{cognito_base_url}/oauth2/authorize?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "provider": provider
    }

# =================================================================
# 소셜 로그인 콜백 처리
# =================================================================
@router.post("/social/callback", response_model=LoginResponse)
async def social_login_callback(
    payload: dict,  # {"code": "..."}
    db: Session = Depends(get_db)
):
    logger.info("[[VERSION 12 START]] Social Login Callback Invoked")
    payload_str = str(payload)
    logger.info(f"Payload: {payload_str}")
    code = payload.get("code")
    if not code:
        raise BusinessException(ErrorCode.INVALID_INPUT_VALUE, "인증 코드가 필요합니다.")
        
    cognito_domain = settings.COGNITO_DOMAIN
    client_id = settings.COGNITO_APP_CLIENT_ID
    redirect_uri = settings.REDIRECT_URI
    
    # Cognito Token Endpoint 호출
    cognito_region = os.getenv("COGNITO_REGION", "ap-northeast-2")
    # [수정] URL 강제 하드코딩에 가깝게 수정 + 로그 추가
    token_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/token"
    
    logger.info(f"[[NEW_VERSION_V11]] Token URL: {token_url}")

    # Client Secret이 필요한 경우 추가해야 함 (현재 설정은 Secret 없는 Public Client 가정)
    # Confidential Client라면 Basic Auth 헤더 필요
    
    async with httpx.AsyncClient() as client:
        # 1. 토큰 교환 (Code -> Tokens)
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri
        }
        
        try:
            token_res = await client.post(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            token_res.raise_for_status()
            tokens = token_res.json()
        except Exception as e:
            logger.error(f"Token exchange failed: {e}, Response: {token_res.text if 'token_res' in locals() else ''}")
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "소셜 로그인 인증 실패 (토큰 교환)")
            
        access_token = tokens.get("access_token")
        id_token = tokens.get("id_token") # JWT with user claims
        
        if not access_token:
             raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "Access Token을 받지 못했습니다.")

        # 2. 사용자 정보 가져오기 (UserInfo Endpoint)
        user_info_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/userInfo"
        user_res = await client.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
        
        if user_res.status_code != 200:
             logger.error(f"UserInfo failed: {user_res.text}")
             raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, "사용자 정보를 가져오는데 실패했습니다.")
             
        user_data = user_res.json()
        email = user_data.get("email")
        sub = user_data.get("sub") # Cognito User Sub (Unique ID)
        
        # 3. DB 사용자 확인 및 자동 가입
        stmt = select(User).where(User.email == email)
        user = db.scalar(stmt)
        
        if not user:
            # 신규 사용자: 자동 회원가입
            # 닉네임이 없으면 이메일 앞부분 사용
            nickname = user_data.get("nickname") or user_data.get("name") or email.split("@")[0]
            
            # 닉네임 중복 처리 (중복 시 랜덤 숫자 추가)
            base_nickname = nickname
            counter = 1
            while db.scalar(select(User).where(User.nickname == nickname)):
                nickname = f"{base_nickname}{counter}"
                counter += 1
            
            new_user = User(
                user_id=str(uuid.uuid4()),
                email=email,
                nickname=nickname,
                password_hash="SOCIAL_LOGIN", # 소셜 로그인 사용자는 비밀번호 없음
                role=UserRole.USER,
                bio=f"Applied via {user_data.get('identities', [{}])[0].get('providerName', 'Social Login')}",
                verified=True # 소셜 로그인은 이미 인증됨
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user
            
        # 4. 앱 내부 토큰 반환 (Cognito 토큰을 그대로 쓸지, 앱 자체 토큰을 발급할지 결정)
        # 여기서는 Cognito가 준 Access Token을 그대로 반환 (프론트가 이걸로 API 호출)
        # 하지만 우리 API는 Gateway가 아니라 직접 호출되므로, 우리 DB의 user 정보도 줘야 함.
        
        return LoginResponse(
            access_token=access_token,
            id_token=id_token, # 선택적
            token_type="Bearer",
            is_success=True,
            user=UserSimple(
                user_id=user.user_id,
                email=user.email,
                nickname=user.nickname,
                role=user.role.value if hasattr(user.role, "value") else user.role,
                profile_image_url=user.profile_image_url,
                myStacks=[s.tech_stack for s in user.stacks],
                liked_project_ids=[]
            )
        )

# [로그아웃 구현은 유지]
@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user: User = Depends(get_current_user) # 토큰으로 현재 사용자 식별
):
    """
    로그아웃 처리:
    실제 토큰 삭제는 클라이언트(프론트)에서 수행하지만,
    서버에서는 '누가 로그아웃 했는지' 보안 로그를 남깁니다.
    """
    # 1. 로그 기록 (Console 또는 파일)
    logger.info(f"User Logout: ID={current_user.id} | Email={current_user.email} | Nickname={current_user.nickname}")
    
    # 2. (선택 사항) 필요하다면 여기서 DB에 '마지막 접속 종료 시간' 등을 업데이트할 수 있습니다.
    
    return {"message": "Successfully logged out"}


# =================================================================
# 7. 회원탈퇴 (Spec: DELETE /users/{user_id})
# =================================================================
@router.delete("/{user_id}", response_model=DeleteAccountResponse)
async def delete_account(
    user_id: str,
    delete_data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Account deletion API:
    1. Ownership check
    2. Cognito delete (password check when provided)
    3. Local DB delete
    """

    # 1. Ownership check
    is_owner = (str(current_user.user_id) == user_id) or (current_user.email == user_id)
    if not is_owner:
        logger.warning(f"Unauthorized deletion attempt: {current_user.email} tried to delete {user_id}")
        raise HTTPException(status_code=403, detail="본인의 계정만 탈퇴할 수 있습니다.")

    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            # 2. Verify password when provided
            if delete_data.password:
                await client.initiate_auth(
                    ClientId=settings.COGNITO_APP_CLIENT_ID,
                    AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={
                        "USERNAME": current_user.email,
                        "PASSWORD": delete_data.password,
                    },
                )

            # 3. Delete user from Cognito (admin)
            await client.admin_delete_user(
                UserPoolId=settings.EFFECTIVE_USER_POOL_ID,
                Username=current_user.email,
            )
        except client.exceptions.NotAuthorizedException:
            raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
        except Exception as e:
            logger.error(f"Cognito Deletion Error: {str(e)}")
            raise HTTPException(status_code=500, detail="인증 서버에서 계정 삭제 중 오류가 발생했습니다.")

    # 4. Delete local user
    try:
        db.delete(current_user)
        db.commit()
        logger.info(f"User Fully Deleted: {current_user.email}")
    except Exception as e:
        db.rollback()
        logger.error(f"DB Deletion Error: {str(e)}")
        raise HTTPException(status_code=500, detail="데이터베이스 정보 삭제 중 오류가 발생했습니다.")

    from datetime import datetime
    return DeleteAccountResponse(
        message="회원탈퇴가 정상적으로 완료되었습니다.",
        deleted_at=datetime.now().isoformat()
    )


# =================================================================
# [추가] 이메일 인증 코드 확인 API
# =================================================================
@router.post("/auth/verify-email")
async def verify_email(verify_in: EmailVerification):
    """
    회원가입 후 이메일로 받은 인증 코드를 확인합니다.
    """
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            await client.confirm_sign_up(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=verify_in.email,
                ConfirmationCode=verify_in.code
            )
            return {"success": True, "code": "AUTH_000", "message": "이메일 인증이 완료되었습니다. 로그인해주세요."}
        except client.exceptions.ExpiredCodeException:
            raise BusinessException(ErrorCode.AUTH_VERIFICATION_CODE_EXPIRED)
        except client.exceptions.CodeMismatchException:
            raise BusinessException(ErrorCode.AUTH_VERIFICATION_CODE_MISMATCH)
        except Exception as e:
            logger.error(f"Email Verify Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_VERIFICATION_CODE_MISMATCH, f"인증 실패: {str(e)}")


# =================================================================
# [추가] 이메일 인증 코드 재발송 API
# =================================================================
@router.post("/auth/resend-code")
async def resend_verification_code(email: str):
    """
    이메일 인증 코드를 다시 발송합니다.
    """
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            await client.resend_confirmation_code(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                Username=email
            )
            return {"success": True, "code": "AUTH_000", "message": "인증 코드가 이메일로 재발송되었습니다."}
        except client.exceptions.UserNotFoundException:
            raise BusinessException(ErrorCode.AUTH_USER_NOT_FOUND)
        except client.exceptions.InvalidParameterException:
            raise BusinessException(ErrorCode.AUTH_ALREADY_VERIFIED)
        except Exception as e:
            logger.error(f"Resend Code Error: {str(e)}")
            raise BusinessException(ErrorCode.AUTH_RESEND_FAILED, f"재발송 실패: {str(e)}")



