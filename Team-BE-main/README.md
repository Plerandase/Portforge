# Portforge - 팀 매칭 플랫폼 백엔드

프로젝트 팀원 모집과 팀 관리를 위한 웹 플랫폼의 백엔드 서비스입니다.

## 🏗️ 서비스 개요

Portforge 백엔드는 다음과 같은 핵심 기능을 제공합니다:

- **프로젝트 생성 및 관리**: 프로젝트 생성, 포지션별 모집인원 설정
- **팀 매칭 시스템**: 지원자 관리, 승인/거절, 자동 모집완료 처리
- **팀 스페이스**: 팀 대시보드, 멤버 관리, 프로젝트 진행 현황
- **사용자 관리**: 회원가입, 로그인, 프로필 관리
- **지원 시스템**: 포지션별 지원, 지원서 관리, 상태 추적

## 🛠️ 기술 스택

- **Framework**: FastAPI 0.104.1
- **Database**: MySQL (SQLAlchemy 2.0 + aiomysql)
- **Authentication**: JWT 토큰 기반 인증
- **Server**: Uvicorn
- **ORM**: SQLAlchemy with async support

## 📁 프로젝트 구조

```
BE/
├── app/
│   ├── api/v1/endpoints/     # API 엔드포인트
│   │   ├── integration.py    # 통합 API (프로젝트, 팀, 지원)
│   │   └── teams.py          # 팀 관리 API
│   ├── core/                 # 핵심 설정
│   │   ├── config.py         # 환경 설정
│   │   └── database.py       # DB 연결 설정
│   ├── models/               # 데이터 모델
│   │   ├── user.py           # 사용자 모델
│   │   ├── project.py        # 프로젝트 및 지원 모델
│   │   ├── team.py           # 팀 관련 모델
│   │   └── enums.py          # Enum 정의
│   └── main.py               # FastAPI 앱
├── create_tables.py          # 데이터베이스 초기화
├── run.py                    # 개발 서버 실행
├── requirements.txt          # Python 의존성
└── .env                      # 환경 변수
```

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가:

```env
# 데이터베이스 설정 (MySQL 사용)
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/my_app_db

# JWT 설정
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS 설정 (향후 확장용)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=ap-northeast-2
S3_BUCKET_NAME=team-platform-bucket
```

### 3. 데이터베이스 설정

MySQL 서버가 실행 중인지 확인 후:

```bash
python create_tables.py
```

### 4. 개발 서버 실행

```bash
python run.py
```

서버가 실행되면:
- **API 서버**: http://localhost:8002
- **API 문서**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

## 📊 데이터베이스 스키마

### 핵심 테이블

1. **users**: 사용자 정보 (user_id, email, nickname, role)
2. **projects**: 프로젝트 정보 (제목, 설명, 기간, 상태)
3. **project_recruitment_positions**: 프로젝트별 모집 포지션 정보
4. **applications**: 지원서 정보 (지원자, 포지션, 상태)
5. **teams**: 팀 정보 (프로젝트별 팀)
6. **team_members**: 팀 멤버 정보 (역할, 포지션)

### 주요 Enum 타입

- **StackCategory**: FRONTEND, BACKEND, DB, INFRA, DESIGN, ETC
- **ApplicationStatus**: PENDING, ACCEPTED, REJECTED
- **ProjectStatus**: RECRUITING, PROCEEDING, COMPLETED, CLOSED
- **TeamRole**: LEADER, MEMBER

## 🔌 주요 API 엔드포인트

### 프로젝트 관리
- `POST /api/v1/integration/create-project-team` - 프로젝트+팀 통합 생성
- `GET /api/v1/integration/projects` - 프로젝트 목록 조회
- `GET /api/v1/integration/project-team-info/{project_id}` - 프로젝트 상세 정보
- `GET /api/v1/integration/project/{project_id}/positions` - 프로젝트 모집 포지션

### 지원 시스템
- `POST /api/v1/integration/project/{project_id}/apply` - 프로젝트 지원하기
- `GET /api/v1/integration/project/{project_id}/applications` - 지원자 목록 조회
- `POST /api/v1/integration/application/{application_id}/approve` - 지원자 승인
- `POST /api/v1/integration/application/{application_id}/reject` - 지원자 거절

### 사용자 관리
- `GET /api/v1/integration/user-projects/{user_id}` - 사용자 참여 프로젝트 목록

## ✨ 주요 기능

### 1. 프로젝트 생성 및 팀 매칭
- 포지션별 모집인원 설정 (프론트엔드, 백엔드, 디자인, DB, 인프라)
- 포지션별 필요 기술스택 설정
- 자동 팀 생성 및 팀장 등록

### 2. 지원 시스템
- 포지션별 지원 기능
- 지원서 상태 관리 (대기중, 승인, 거절)
- 팀장의 지원자 관리 (승인/거절)

### 3. 자동 모집완료 처리
- 모든 포지션이 다 찬 경우 자동으로 '모집완료' 상태로 변경
- 모집완료된 프로젝트는 지원 불가 처리

### 4. 팀 관리
- 팀장은 PM으로 표시
- 팀 멤버 목록 및 역할 관리
- 팀 스페이스 대시보드

## 🔧 개발 가이드

### 새로운 API 추가

1. **모델 정의**: `app/models/`에 필요한 모델 추가
2. **API 엔드포인트**: `app/api/v1/endpoints/integration.py`에 새 엔드포인트 추가
3. **라우터 등록**: `app/main.py`에서 라우터 확인

### 데이터베이스 스키마 변경

```bash
# 스키마 변경 후 테이블 재생성
python create_tables.py
```

## 🧪 테스트

개발 중 API 테스트:
- Swagger UI: http://localhost:8002/docs
- 직접 API 호출로 기능 테스트

## 📈 현재 구현 상태

✅ **완료된 기능**
- 프로젝트 생성 및 팀 생성
- 포지션별 지원 시스템
- 지원자 승인/거절
- 자동 모집완료 처리
- 팀 스페이스 기본 기능
- 사용자 프로젝트 목록

🚧 **향후 계획**
- 실시간 채팅 시스템
- 파일 공유 기능
- 회의 관리 시스템
- 칸반 보드
- 알림 시스템

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.


pod 생성 알림 되냐 이거???
왜 안되냐고
tlqkfwlsWk
rotlqkf toZlEE

dsfadsfdsftlqkfqudtlsrkxdms rotoRldiㄴㅇㄴㅇㄴ
sdfalksjdflksdjflkdsajflksdajffsadfdsfsdafds
fsdafsdafsdfdsfds
