# FastAPI + AWS Cognito 인증 시스템

AWS Cognito를 활용한 완전한 사용자 인증 시스템입니다. 회원가입, 로그인, 소셜 로그인, 비밀번호 관리, 회원탈퇴 등의 기능을 제공합니다.

## 🚀 주요 기능

- **완전한 사용자 인증**: AWS Cognito 기반 보안 인증
- **소셜 로그인**: Google OAuth 지원
- **비밀번호 관리**: 변경, 찾기, 재설정
- **회원탈퇴**: 안전한 계정 삭제
- **로컬 DB 연동**: MySQL과 Cognito 데이터 동기화
- **개발 환경**: Docker로 로컬 인프라 구성

## 📋 필수 프로그램 설치

아래 프로그램들이 설치되어 있어야 합니다:

1. **Python (3.13 이상)**: https://www.python.org/downloads/
   - 설치 시 "Add Python to PATH" 옵션 체크 필수

2. **Poetry**: Python 패키지 관리자
   ```bash
   # Windows (PowerShell)
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   
   # macOS/Linux
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - 설치 후 Docker Desktop 실행 필수

4. **Git**: https://git-scm.com/downloads

## 🛠️ 설치 및 실행

### Step 1: 프로젝트 클론
```bash
git clone <repository-url>
cd backend/auth_branch
```

### Step 2: 의존성 설치
```bash
poetry install --no-root
```

### Step 3: 환경변수 설정
```bash
# .env.example을 복사하여 .env 파일 생성
poetry run poe copy-env
```

생성된 `.env` 파일을 열어 AWS Cognito 정보를 입력하세요:
```env
# AWS Cognito 설정 (실제 값으로 교체 필요)
COGNITO_REGION=ap-northeast-2
COGNITO_USERPOOL_ID=ap-northeast-2_xxxxxxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_DOMAIN="https://your-domain.auth.ap-northeast-2.amazoncognito.com"
REDIRECT_URI="http://localhost:3000/"
```

### Step 4: 로컬 인프라 실행
```bash
# MySQL, DynamoDB, MinIO 컨테이너 실행
poetry run poe db-up
```

### Step 5: 데이터베이스 마이그레이션
```bash
# 데이터베이스 테이블 생성
poetry run poe migrate
```

### Step 6: 애플리케이션 실행
```bash
# FastAPI 서버 실행 (http://localhost:8000)
poetry run poe run
```

## 📚 주요 패키지

### 핵심 의존성
- **FastAPI**: 고성능 웹 프레임워크
- **aioboto3**: AWS SDK (비동기)
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Alembic**: 데이터베이스 마이그레이션
- **Pydantic**: 데이터 검증 및 직렬화
- **python-jose**: JWT 토큰 처리
- **httpx**: HTTP 클라이언트 (소셜 로그인용)

### 데이터베이스
- **aiomysql**: MySQL 비동기 드라이버
- **pymysql**: MySQL 동기 드라이버

### 개발 도구
- **ruff**: 코드 포맷팅 및 린팅
- **poethepoet**: 태스크 러너
- **uvicorn**: ASGI 서버

## 🔧 개발 명령어

```bash
# 개발 서버 실행
poetry run poe run

# 코드 포맷팅 및 린팅
poetry run poe lint

# 데이터베이스 관련
poetry run poe db-up      # 컨테이너 시작
poetry run poe db-down    # 컨테이너 중지
poetry run poe db-clean   # 컨테이너 및 볼륨 삭제

# 마이그레이션
poetry run poe makemigrations  # 새 마이그레이션 생성
poetry run poe migrate         # 마이그레이션 적용
```

## 📖 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 🔐 인증 API

#### 회원가입
```http
POST /auth/join
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "nickname": "사용자닉네임"
}
```

#### 로그인
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### 소셜 로그인 (Google)
```http
POST /auth/social/callback
Content-Type: application/json

{
  "code": "google_oauth_code"
}
```

#### 내 정보 조회
```http
GET /users/me
Authorization: Bearer {access_token}
```

#### 비밀번호 변경
```http
PUT /users/{user_id}/password
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "old_password": "현재비밀번호",
  "new_password": "새비밀번호"
}
```

#### 회원탈퇴
```http
DELETE /users/{user_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "password": "현재비밀번호",
  "reason": "탈퇴사유 (선택사항)"
}
```

### 🔧 유틸리티 API

#### 닉네임 중복 확인
```http
GET /auth/validate_nickname?nickname=테스트닉네임
```

#### 이메일 인증
```http
POST /auth/verify-email
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}
```

#### 비밀번호 찾기
```http
# 1단계: 인증코드 요청
POST /auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}

# 2단계: 비밀번호 재설정
POST /auth/confirm-forgot-password
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "새비밀번호"
}
```

## 🏗️ 프로젝트 구조

```
backend/auth_branch/
├── app/
│   ├── api/
│   │   ├── auth.py          # 인증 관련 API
│   │   └── deps.py          # 의존성 주입
│   ├── core/
│   │   ├── config.py        # 설정 관리
│   │   ├── database.py      # DB 연결
│   │   ├── security.py      # 보안 유틸리티
│   │   └── exceptions.py    # 예외 처리
│   ├── models/
│   │   └── user.py          # 사용자 모델
│   ├── schemas/
│   │   └── user.py          # Pydantic 스키마
│   └── main.py              # FastAPI 앱
├── alembic/                 # 데이터베이스 마이그레이션
├── docker-compose.yml       # 로컬 인프라
├── pyproject.toml          # 프로젝트 설정
├── .env.example            # 환경변수 템플릿
└── README.md               # 이 파일
```

## 🔒 보안 고려사항

1. **환경변수**: `.env` 파일은 절대 Git에 커밋하지 마세요
2. **토큰 관리**: JWT 토큰은 클라이언트에서 안전하게 저장하세요
3. **비밀번호**: AWS Cognito 정책에 따라 강력한 비밀번호 사용
4. **CORS**: 프로덕션에서는 허용된 도메인만 설정하세요

## 🌐 AWS Cognito 설정

### 필요한 Cognito 설정:
1. **User Pool 생성**
2. **App Client 생성** (Public Client)
3. **OAuth 설정**: Google 등 소셜 로그인 제공자 추가
4. **도메인 설정**: 호스팅된 UI용 도메인 구성
5. **콜백 URL**: `http://localhost:3000/` 등록

### 환경변수 매핑:
- `COGNITO_USERPOOL_ID`: User Pool ID
- `COGNITO_APP_CLIENT_ID`: App Client ID  
- `COGNITO_DOMAIN`: 호스팅된 UI 도메인
- `REDIRECT_URI`: 프론트엔드 콜백 URL

## 🐛 문제 해결

### 일반적인 문제들:

1. **Docker 컨테이너 실행 실패**
   ```bash
   # Docker Desktop이 실행 중인지 확인
   docker --version
   
   # 포트 충돌 확인 (3306, 8001, 9000)
   netstat -an | findstr "3306"
   ```

2. **Cognito 인증 실패**
   - `.env` 파일의 Cognito 설정값 확인
   - AWS 콘솔에서 User Pool 상태 확인
   - 네트워크 연결 상태 확인

3. **데이터베이스 연결 실패**
   ```bash
   # MySQL 컨테이너 상태 확인
   docker ps
   
   # 로그 확인
   docker logs template-mysql
   ```

## 📞 지원

- **API 문서**: http://localhost:8000/docs
- **프로젝트 이슈**: GitHub Issues 활용
- **AWS Cognito 문서**: https://docs.aws.amazon.com/cognito/

---

**주의**: 이 프로젝트는 개발 환경용으로 구성되어 있습니다. 프로덕션 배포 시에는 추가적인 보안 설정이 필요합니다.