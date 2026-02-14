**프론트엔드**: React 18 + TypeScript + Vite + Tailwind CSS  
**백엔드**: FastAPI + SQLAlchemy (비동기) + Alembic  
**데이터베이스**: MySQL 8.0 + Docker  

## 🚀 실행 방법

### 백엔드
```bash
cd Project-main
poetry install
docker-compose up -d
poetry run alembic upgrade head
poetry run poe run  # http://127.0.0.1:8000
```

### 프론트엔드
```bash
cd FE
npm install
npm run dev  # http://localhost:3001
```

## 📊 구현 현황

### ✅ 완료된 기능

#### 핵심 인프라
- [x] FastAPI + SQLAlchemy (비동기) 구성
- [x] MySQL 8.0 + Docker 컨테이너화
- [ ] Alembic 마이그레이션
- [x] CORS 설정
- [x] 메모리 폴백 시스템 (DB 연결 실패 처리)
- [x] 에러 처리 및 로깅

#### API 엔드포인트
- [x] **프로젝트 관리**
  - `GET/POST /recruitment-projects` - CRUD 작업
  - `GET /recruitment-projects/{id}` - 프로젝트 상세
- [x] **지원서 시스템**
  - `POST /recruitment-projects/{id}/applications` - 지원서 제출
  - `GET /recruitment-projects/{id}/applications` - 지원자 목록 (팀장용)
  - `PATCH /applications/{id}/status` - 지원서 승인/거절
  - `GET /applications/{id}` - 지원서 상세

#### 비즈니스 로직
- [x] **8개 필드 지원서 폼**
  - 지원동기(필수), 경력(필수), 포트폴리오 URL
  - 참여시간, 연락처, 보유기술, 질문사항
- [x] **AI 역량 테스트**
  - 포지션별 문제 생성
  - 실시간 타이머 (30초/문제)
  - 자동 채점 및 수준 평가
- [x] **팀장 관리 대시보드**
  - 지원자 목록 및 통계
  - AI 분석 도우미
  - 승인/거절 워크플로우

#### 프론트엔드 기능
- [x] React + TypeScript 아키텍처
- [x] 프로젝트 생성 및 목록
- [x] 상세 지원서 모달 시스템
- [x] 실시간 모집 현황
- [x] 개인정보 보호 (이름 마스킹)
- [x] 역할 기반 UI (관리자/사용자)

## 🏗 MSA 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   프론트엔드     │    │   백엔드        │    │   데이터베이스   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (MySQL 8.0)   │
│   포트: 3001    │    │   포트: 8000    │    │   포트: 3306    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 데이터베이스 스키마
```sql
-- 구현된 핵심 테이블
recruitment_projects     # 프로젝트 정보
recruitment_positions    # 프로젝트별 포지션 요구사항
applications            # 8개 필드 사용자 지원서
```

### API 구조
```
app/
├── controllers/        # API 엔드포인트
├── models/            # SQLAlchemy 모델
├── repositories/      # 데이터 접근 계층
├── schemas/          # Pydantic 검증
└── core/             # 데이터베이스 및 의존성
```

## 📋 개발 체크리스트

### 백엔드 진행도
- [x] 프로젝트 CRUD 작업
- [x] 지원서 제출 시스템
- [x] 팀장 관리 API
- [x] 데이터베이스 마이그레이션 (Alembic)
- [x] Docker 컨테이너화
- [x] 메모리 폴백 시스템
- [ ] 인증 미들웨어
- [ ] 파일 업로드 엔드포인트

### 프론트엔드 진행도
- [x] 프로젝트 목록 및 생성
- [x] 8개 필드 지원서 폼
- [x] AI 테스트 연동
- [x] 팀장 대시보드
- [x] 반응형 디자인
- [ ] 인증 플로우
- [ ] 파일 업로드 UI
- [ ] 실시간 업데이트

## 🔗 API 문서

**Swagger UI**: http://127.0.0.1:8000/docs  
**상태 확인**: http://127.0.0.1:8000/health

### 주요 엔드포인트
```
GET    /recruitment-projects          # 프로젝트 목록
POST   /recruitment-projects          # 프로젝트 생성
GET    /recruitment-projects/{id}     # 프로젝트 상세
POST   /recruitment-projects/{id}/applications  # 지원서 제출
GET    /recruitment-projects/{id}/applications  # 지원자 목록
PATCH  /applications/{id}/status      # 지원서 상태 변경
```

## 📁 프로젝트 구조

```
Final_main/
├── FE/                    # React 프론트엔드
│   ├── api/              # API 클라이언트
│   ├── contexts/         # 상태 관리
│   └── pages/            # 페이지 컴포넌트
└── Project-main/         # FastAPI 백엔드
    ├── app/
    │   ├── controllers/  # API 엔드포인트
    │   ├── models/       # 데이터베이스 모델
    │   ├── repositories/ # 데이터 접근
    │   └── schemas/      # 검증
    ├── migrations/       # Alembic 마이그레이션
    └── docker-compose.yml
```

---

**현재 상태**: 8개 필드 지원서, AI 테스트, 팀 관리 기능이 포함된 핵심 지원 시스템 완전 구현. 인증 및 고급 기능 개발 준비 완료.

## 백엔드 명령어
```
poetry install  // 프로젝트 초기화 및 의존성 설치

poetry add fastapi uvicorn sqlalchemy alembic // 새 패키지 추가

poetry shell // 가상환경 활성화

poetry add --group dev pytest black isort // 개발 의존성 추가

poetry show // 의존성 목록 확인
```

## FastAPI 서버 실행
```
★ poetry run poe run ★ // 서버 실행

poetry run uvicorn app.main:app --reload --port 8000 --host 127.0.0.1 // 특정 포트로 실행
```

## Docker 관련
```
docker-compose up -d // docker 컨테이너 시작

docker-compose down // docker 컨테이너 중지

docker-compose down -v // 볼륨까지 삭제

docker exec -it project-main-mysql-1 mysql -u root -prootpassword // DB접속
```



wpsdkfjlksdjaflkjsdlf