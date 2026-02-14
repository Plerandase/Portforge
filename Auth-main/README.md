# PortForge 프로젝트 - Auth 서비스

## 1. 서비스 개요

### 1.1 개요
Auth Service는 PortForge 플랫폼의 사용자 인증 및 계정 관리를 담당하는 마이크로서비스입니다. AWS Cognito를 기반으로 안전한 인증 체계를 구축하고, 로컬 RDS와 동기화하여 사용자 데이터를 관리합니다.

| 항목 | 내용 |
|------|------|
| 서비스명 | Auth Service |
| 포트 | 8000 |
| 도메인 | https://portforge.org |
| API 경로 | /auth/*, /users/* |
| Replicas | 2 |

### 1.2 핵심 기능

#### 1.2.1 회원가입 (Sign Up)

**기능 설명**
- 이메일, 비밀번호, 닉네임을 입력받아 새로운 사용자 계정을 생성합니다.
- AWS Cognito에 먼저 사용자를 등록한 후, 로컬 RDS에 동기화합니다.
- Cognito에서 발급한 `sub` (UUID)를 로컬 DB의 `user_id`로 사용하여 데이터 일관성을 유지합니다.
- RDS 저장 실패 시 Cognito 계정을 롤백하여 데이터 불일치를 방지합니다.
- 회원가입 시 기술 스택(Tech Stack)도 함께 저장할 수 있습니다.

**핵심 로직**
```python
@router.post("/join", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. 로컬 DB 중복 검사
    if db.scalar(select(User).where(User.email == user_in.email)):
        raise BusinessException(ErrorCode.AUTH_EMAIL_DUPLICATE)
    if db.scalar(select(User).where(User.nickname == user_in.nickname)):
        raise BusinessException(ErrorCode.AUTH_NICKNAME_DUPLICATE)

    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        # 2. AWS Cognito 회원가입
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
            cognito_sub = response["UserSub"]  # Cognito에서 발급한 고유 ID
            
        except client.exceptions.UsernameExistsException:
            raise BusinessException(ErrorCode.AUTH_COGNITO_USER_EXISTS)
        except client.exceptions.InvalidPasswordException:
            raise BusinessException(ErrorCode.AUTH_INVALID_PASSWORD_FORMAT)

        # 3. 로컬 DB 저장 (실패 시 Cognito 롤백)
        try:
            new_user = User(
                user_id=cognito_sub,  # Cognito sub를 PK로 사용
                email=user_in.email,
                nickname=user_in.nickname,
                role=UserRole.USER,
                test_count=5
            )
            db.add(new_user)
            
            # 기술 스택 저장
            for stack in user_in.stacks:
                new_stack = UserStack(
                    user_id=cognito_sub,
                    position_type=stack.position_type,
                    stack_name=stack.stack_name
                )
                db.add(new_stack)

            db.commit()
            return new_user

        except Exception as db_error:
            db.rollback()
            # Cognito 계정 롤백 (삭제)
            await client.admin_delete_user(
                UserPoolId=settings.EFFECTIVE_USER_POOL_ID,
                Username=user_in.email
            )
            raise BusinessException(ErrorCode.INTERNAL_SERVER_ERROR)
```

---

#### 1.2.2 로그인 (Login)

**기능 설명**
- 이메일과 비밀번호를 입력받아 사용자 인증을 수행합니다.
- Cognito의 `USER_PASSWORD_AUTH` 플로우를 사용하여 인증합니다.
- 인증 성공 시 Access Token, ID Token을 발급하고 사용자 정보를 함께 반환합니다.
- 이메일 미인증, 잘못된 비밀번호 등 다양한 예외 상황을 처리합니다.

**핵심 로직**
```python
@router.post("/login", response_model=LoginResponse)
async def login(user_in: UserLogin, db: Session = Depends(get_db)):
    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        try:
            # Cognito 인증 요청
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

    # 로컬 DB에서 사용자 정보 조회
    user = db.scalar(select(User).where(User.email == user_in.email))
    if not user:
        raise BusinessException(ErrorCode.USER_NOT_FOUND)

    return {
        "access_token": auth_result["AccessToken"],
        "id_token": auth_result.get("IdToken"),
        "token_type": auth_result["TokenType"],
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "nickname": user.nickname,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "myStacks": user.myStacks,
            "test_count": user.test_count,
            "liked_project_ids": user.liked_project_ids or []
        }
    }
```

---

#### 1.2.3 소셜 로그인 (Social Login - Google OAuth)

**기능 설명**
- Google OAuth 2.0을 통한 소셜 로그인을 지원합니다.
- Cognito Hosted UI를 활용하여 OAuth 플로우를 처리합니다.
- 신규 사용자는 자동으로 회원가입 처리되며, 기존 사용자는 로그인됩니다.
- 닉네임 중복 시 자동으로 숫자를 붙여 고유한 닉네임을 생성합니다.

**플로우**
```
1. 프론트엔드 → GET /auth/social/login-url?provider=Google
2. 백엔드 → Cognito OAuth URL 반환
3. 사용자 → Google 로그인 페이지에서 인증
4. Cognito → 프론트엔드 콜백 URL로 authorization code 전달
5. 프론트엔드 → POST /auth/social/callback (code)
6. 백엔드 → Cognito Token Endpoint에서 code를 token으로 교환
7. 백엔드 → UserInfo Endpoint에서 사용자 정보 조회
8. 백엔드 → DB에 사용자 생성/조회 후 토큰과 함께 반환
```

**핵심 로직**
```python
@router.get("/social/login-url")
async def get_social_login_url(provider: str):
    """소셜 로그인 URL 생성"""
    cognito_domain = settings.COGNITO_DOMAIN
    client_id = settings.COGNITO_APP_CLIENT_ID
    redirect_uri = settings.REDIRECT_URI
    
    provider_map = {"Google": "Google", "Kakao": "Kakao"}
    identity_provider = provider_map.get(provider)
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "identity_provider": identity_provider,
        "scope": "openid email profile",
        "prompt": "select_account"
    }
    
    auth_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/authorize?{urlencode(params)}"
    return {"auth_url": auth_url, "provider": provider}


@router.post("/social/callback", response_model=LoginResponse)
async def social_login_callback(payload: dict, db: Session = Depends(get_db)):
    """소셜 로그인 콜백 처리"""
    code = payload.get("code")
    
    async with httpx.AsyncClient() as client:
        # 1. Code → Token 교환
        token_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/token"
        token_res = await client.post(token_url, data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri
        })
        tokens = token_res.json()
        access_token = tokens.get("access_token")
        
        # 2. 사용자 정보 조회
        user_info_url = f"https://{cognito_domain}.auth.{cognito_region}.amazoncognito.com/oauth2/userInfo"
        user_res = await client.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
        user_data = user_res.json()
        
    email = user_data.get("email")
    sub = user_data.get("sub")
    
    # 3. DB 사용자 확인 및 자동 가입
    user = db.scalar(select(User).where(User.email == email))
    
    if not user:
        nickname = user_data.get("nickname") or email.split("@")[0]
        # 닉네임 중복 처리
        while db.scalar(select(User).where(User.nickname == nickname)):
            nickname = f"{nickname}{random.randint(1000, 9999)}"
        
        user = User(user_id=sub, email=email, nickname=nickname, role=UserRole.USER)
        db.add(user)
        db.commit()
    
    return LoginResponse(access_token=access_token, id_token=tokens.get("id_token"), user=user)
```

---

#### 1.2.4 비밀번호 관리

**기능 설명**
- **비밀번호 변경**: 로그인된 사용자가 현재 비밀번호를 확인 후 새 비밀번호로 변경
- **비밀번호 찾기**: 이메일로 인증 코드 발송
- **비밀번호 재설정**: 인증 코드 확인 후 새 비밀번호 설정

**핵심 로직**
```python
# 비밀번호 변경
@router.put("/{user_id}/password")
async def change_password(user_id: str, data: PasswordChange, authorization: str = Header(None)):
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


# 비밀번호 찾기 (인증 코드 요청)
@router.post("/forgot-password")
async def forgot_password_request(data: ForgotPasswordRequest):
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        await client.forgot_password(
            ClientId=settings.COGNITO_APP_CLIENT_ID, 
            Username=data.email
        )
        return {"message": "인증 코드가 이메일로 발송되었습니다."}


# 비밀번호 재설정
@router.post("/confirm-forgot-password")
async def confirm_forgot_password(data: ConfirmForgotPassword):
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        await client.confirm_forgot_password(
            ClientId=settings.COGNITO_APP_CLIENT_ID,
            Username=data.email,
            ConfirmationCode=data.code,
            Password=data.new_password
        )
        return {"message": "비밀번호가 성공적으로 재설정되었습니다."}
```

---

#### 1.2.5 프로필 관리

**기능 설명**
- **내 정보 조회**: 현재 로그인한 사용자의 상세 정보 조회
- **내 정보 수정**: 닉네임, 프로필 이미지, 기술 스택 수정
- **프로필 이미지 업로드**: S3에 이미지 업로드 후 URL 저장

**핵심 로직**
```python
# 내 정보 조회
@router.get("/me", response_model=UserDetailResponse)
async def get_user_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_query = select(User).where(User.user_id == current_user.user_id)
    result = await db.execute(user_query)
    user = result.scalar_one()

    stacks_query = select(UserStack).where(UserStack.user_id == user.user_id)
    stacks_result = await db.execute(stacks_query)
    stacks = stacks_result.scalars().all()
    
    return UserDetailResponse(
        user_id=user.user_id,
        email=user.email,
        nickname=user.nickname,
        role=user.role,
        profile_image_url=user.profile_image_url,
        liked_project_ids=user.liked_project_ids or [],
        stacks=[UserStackResponse(...) for stack in stacks]
    )


# 내 정보 수정 (기술 스택 포함)
@router.put("/me")
async def update_user_me(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await db.execute(select(User).where(User.user_id == current_user.user_id))
    user = user.scalar_one()

    if user_data.name:
        user.nickname = user_data.name
    
    if user_data.profile_image_url is not None:
        user.profile_image_url = user_data.profile_image_url
        
    # 기술 스택 전체 교체
    if user_data.myStacks is not None:
        await db.execute(delete(UserStack).where(UserStack.user_id == user.user_id))
        
        for s_name in user_data.myStacks:
            category = get_stack_category(s_name)  # 스택명으로 카테고리 자동 분류
            new_stack = UserStack(user_id=user.user_id, position_type=category, stack_name=s_name)
            db.add(new_stack)

    await db.commit()
    return {"message": "프로필이 업데이트되었습니다."}
```

---

#### 1.2.6 프로젝트 좋아요

**기능 설명**
- 사용자가 프로젝트에 좋아요를 누르거나 취소할 수 있습니다.
- 토글 방식으로 동작하며, 이미 좋아요한 프로젝트는 취소됩니다.
- 좋아요한 프로젝트 ID 목록은 JSON 배열로 저장됩니다.

**핵심 로직**
```python
@router.post("/me/likes/{project_id}")
async def toggle_like_project(project_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await db.execute(select(User).where(User.user_id == current_user.user_id))
    user = user.scalar_one()
    
    liked = list(user.liked_project_ids or [])
    
    if project_id in liked:
        liked.remove(project_id)  # 좋아요 취소
        action = "removed"
    else:
        liked.append(project_id)  # 좋아요 추가
        action = "added"
        
    user.liked_project_ids = liked
    await db.commit()
    
    return {
        "project_id": project_id,
        "action": action,
        "liked_project_ids": liked
    }
```

---

#### 1.2.7 회원탈퇴

**기능 설명**
- 사용자가 자신의 계정을 삭제할 수 있습니다.
- 비밀번호 확인 후 Cognito와 로컬 DB에서 동시에 삭제합니다.
- 본인 계정만 삭제할 수 있도록 권한 검증을 수행합니다.

**핵심 로직**
```python
@router.delete("/{user_id}", response_model=DeleteAccountResponse)
async def delete_account(
    user_id: str,
    delete_data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. 본인 확인
    is_owner = (str(current_user.user_id) == user_id)
    if not is_owner:
        raise HTTPException(status_code=403, detail="본인의 계정만 탈퇴할 수 있습니다.")

    session = aioboto3.Session()
    async with session.client("cognito-idp", region_name=settings.AWS_REGION) as client:
        # 2. 비밀번호 확인
        if delete_data.password:
            await client.initiate_auth(
                ClientId=settings.COGNITO_APP_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": current_user.email,
                    "PASSWORD": delete_data.password,
                },
            )
        
        # 3. Cognito에서 삭제
        await client.admin_delete_user(
            UserPoolId=settings.EFFECTIVE_USER_POOL_ID,
            Username=current_user.email,
        )

    # 4. 로컬 DB에서 삭제 (Cascade로 UserStack도 함께 삭제)
    user = await db.execute(select(User).where(User.user_id == current_user.user_id))
    user = user.scalar_one()
    await db.delete(user)
    await db.commit()

    return DeleteAccountResponse(
        message="회원탈퇴가 정상적으로 완료되었습니다.",
        deleted_at=datetime.now().isoformat()
    )
```

### 1.3 기술적 특징

#### Cognito-RDS 동기화
- 회원가입 시 Cognito에 먼저 등록 후 RDS에 저장
- RDS 저장 실패 시 Cognito 롤백 처리
- Cognito sub를 user_id로 사용하여 일관성 유지

#### 비동기 처리
- aioboto3를 사용한 AWS SDK 비동기 호출
- aiomysql을 사용한 비동기 DB 연결
- httpx를 사용한 비동기 HTTP 클라이언트

#### 토큰 검증
- Cognito JWKS를 통한 JWT 토큰 검증
- RS256 알고리즘 사용
- Access Token 만료 시간: 30분

### 1.4 데이터 모델

#### Users 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| user_id | CHAR(36) | PK, Cognito sub |
| email | VARCHAR(100) | 이메일 (Unique) |
| nickname | VARCHAR(20) | 닉네임 |
| role | ENUM | USER, ADMIN |
| profile_image_url | TEXT | 프로필 이미지 URL |
| liked_project_ids | JSON | 좋아요한 프로젝트 ID 배열 |
| test_count | INT | 테스트 횟수 (기본값: 5) |
| created_at | DATETIME | 생성일시 |
| updated_at | DATETIME | 수정일시 |

#### User_Stacks 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| stack_id | BIGINT | PK, Auto Increment |
| user_id | CHAR(36) | FK → users.user_id |
| position_type | ENUM | FRONTEND, BACKEND, DB, INFRA, DESIGN, ETC |
| stack_name | VARCHAR(50) | 기술 스택명 |
| created_at | DATETIME | 생성일시 |
| updated_at | DATETIME | 수정일시 |

### 1.5 API 엔드포인트

#### 인증 API (/auth)
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | /auth/join | 회원가입 |
| POST | /auth/login | 로그인 |
| POST | /auth/logout | 로그아웃 |
| GET | /auth/validate_nickname | 닉네임 중복 확인 |
| POST | /auth/verify-email | 이메일 인증 |
| POST | /auth/forgot-password | 비밀번호 찾기 요청 |
| POST | /auth/confirm-forgot-password | 비밀번호 재설정 |
| GET | /auth/social/login-url | 소셜 로그인 URL 생성 |
| POST | /auth/social/callback | 소셜 로그인 콜백 |

#### 사용자 API (/users)
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | /users/me | 내 정보 조회 |
| PUT | /users/me | 내 정보 수정 |
| PUT | /users/{user_id}/password | 비밀번호 변경 |
| POST | /users/{user_id}/profile-image | 프로필 이미지 업로드 |
| POST | /users/me/likes/{project_id} | 프로젝트 좋아요 토글 |
| DELETE | /users/{user_id} | 회원탈퇴 |
| GET | /users/{user_id} | 사용자 상세 조회 |
| POST | /users/batch | 사용자 배치 조회 |

#### 헬스체크
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | /health | 서비스 상태 확인 |

### 1.6 성능 지표

| 지표 | 값 |
|------|-----|
| 평균 응답 시간 | < 200ms |
| Health Check 간격 | 5초 |
| Liveness Probe | /health (30초 후 시작) |
| Readiness Probe | /health (10초 후 시작) |

#### 리소스 할당
| 항목 | Request | Limit |
|------|---------|-------|
| CPU | 100m | 250m |
| Memory | 256Mi | 512Mi |

### 1.7 보안 및 안정성

#### 인증 보안
- AWS Cognito 기반 인증 (AWS 관리형 서비스)
- JWT RS256 알고리즘 사용
- JWKS를 통한 토큰 서명 검증
- Access Token 30분 만료

#### 비밀번호 정책
- Cognito 기본 정책 적용
- 최소 8자 이상
- 대문자, 소문자, 숫자, 특수문자 포함

#### CORS 설정
```
허용 도메인:
- https://portforge.org
- https://*.amazoncognito.com
- https://*.amazonaws.com
```

#### 예외 처리
- BusinessException을 통한 일관된 에러 응답
- ErrorCode 기반 에러 코드 관리
- 상세 로깅 (api_logger)

### 1.8 환경 설정

#### ConfigMap (auth-service-config)
| 키 | 값 |
|-----|-----|
| ENV | production |
| DEBUG | false |
| COGNITO_REGION | ap-northeast-2 |
| COGNITO_USER_POOL_ID | ap-northeast-2_4DwI5MdtT |
| COGNITO_APP_CLIENT_ID | 1lll548h0fo0blhnerb3n1s31d |
| REDIRECT_URI | https://portforge.org/auth/callback |

#### Secret (auth-service-secrets)
| 키 | 설명 |
|-----|------|
| database-url | RDS 연결 URL |
| secret-key | JWT Secret Key |
| aws-access-key | AWS Access Key |
| aws-secret-key | AWS Secret Key |
| cognito-userpool-id | Cognito User Pool ID |

### 1.9 프론트엔드 연동

#### 로그인 플로우
```
1. 프론트엔드 → POST /auth/login (email, password)
2. Auth Service → Cognito 인증
3. Auth Service → 프론트엔드 (access_token, id_token, user 정보)
4. 프론트엔드 → localStorage에 토큰 저장
5. 이후 API 호출 시 Authorization: Bearer {token} 헤더 포함
```

#### 소셜 로그인 플로우
```
1. 프론트엔드 → GET /auth/social/login-url?provider=Google
2. Auth Service → Cognito OAuth URL 반환
3. 프론트엔드 → Cognito 로그인 페이지로 리다이렉트
4. 사용자 → Google 로그인
5. Cognito → 프론트엔드 콜백 URL로 code 전달
6. 프론트엔드 → POST /auth/social/callback (code)
7. Auth Service → Cognito 토큰 교환 → 사용자 정보 조회/생성
8. Auth Service → 프론트엔드 (access_token, user 정보)
```

#### 토큰 갱신
- 현재 Refresh Token 자동 갱신 미구현
- Access Token 만료 시 재로그인 필요

### 1.10 개발 및 배포

#### 로컬 개발
```bash
cd auth
poetry install --no-root
cp .env.example .env
poetry run uvicorn app.main:app --reload --port 8000
```

#### Docker 빌드
```bash
docker build -t auth-service .
```

#### ECR 푸시
```bash
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com
docker tag auth-service:latest 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/auth-service:latest
docker push 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/auth-service:latest
```

#### K8s 배포
```bash
kubectl apply -f k8s/Auth/
kubectl rollout restart deployment/auth-deployment
```

#### CI/CD
- GitHub Actions를 통한 자동 빌드/배포
- ArgoCD를 통한 GitOps 배포 관리

---

## 2. 기술 스택 상세

### 2.1 백엔드

| 분류 | 기술 | 버전 | 용도 |
|------|------|------|------|
| Framework | FastAPI | 0.115+ | 웹 프레임워크 |
| ORM | SQLAlchemy | 2.0+ | 데이터베이스 ORM |
| Migration | Alembic | - | DB 마이그레이션 |
| Validation | Pydantic | 2.0+ | 데이터 검증 |
| AWS SDK | aioboto3 | - | AWS 서비스 연동 (비동기) |
| HTTP Client | httpx | - | 외부 API 호출 |
| JWT | python-jose | - | 토큰 처리 |
| DB Driver | aiomysql | - | MySQL 비동기 드라이버 |
| Server | Uvicorn | - | ASGI 서버 |
| Monitoring | prometheus-fastapi-instrumentator | - | 메트릭 수집 |

### 2.2 인프라

| 분류 | 기술 | 설명 |
|------|------|------|
| Container | Docker | 컨테이너화 |
| Orchestration | Kubernetes (EKS) | 컨테이너 오케스트레이션 |
| Registry | Amazon ECR | 컨테이너 이미지 저장소 |
| Database | Amazon RDS (MySQL 8.4.7) | 관계형 데이터베이스 |
| Auth | AWS Cognito | 사용자 인증/관리 |
| Storage | Amazon S3 | 프로필 이미지 저장 |
| Load Balancer | AWS ALB | 로드 밸런싱 |
| DNS | Route 53 | DNS 관리 |
| SSL | AWS ACM | SSL 인증서 |
| CI/CD | GitHub Actions + ArgoCD | 자동 배포 |
| Monitoring | Prometheus + Grafana | 모니터링 |
| Logging | Loki + Promtail | 로그 수집 |

---

## 3. 향후 개선 사항

| 우선순위 | 항목 | 설명 |
|----------|------|------|
| 🔴 높음 | Secret 관리 | K8s Secret → AWS Secrets Manager 전환 |
| 🔴 높음 | Refresh Token | 토큰 자동 갱신 구현 |
| 🟡 중간 | Rate Limiting | API 호출 제한 구현 |
| 🟡 중간 | 2FA | 2단계 인증 지원 |
| 🟢 낮음 | 소셜 로그인 확장 | Kakao, Naver, GitHub 추가 |

---

## 4. 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [AWS Cognito 개발자 가이드](https://docs.aws.amazon.com/cognito/)
- [SQLAlchemy 2.0 문서](https://docs.sqlalchemy.org/)
- API 문서: https://api.portforge.org/docs
