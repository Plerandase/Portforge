# Portforge AI Service

회의록 자동 생성 AI 서비스 (MSA 아키텍처)

## 아키텍처

```
[프론트엔드] → [채팅 서비스] → [DynamoDB]
                    ↓
              [AI 서비스] → [Bedrock] → [S3]
                    ↓
                 [MySQL]
```

## 주요 기능

- 채팅 메시지 저장 (DynamoDB)
- 회의 시작/종료 관리
- AI 기반 회의록 자동 생성 (AWS Bedrock - Claude 3.5)
- 회의록 S3 저장 및 조회

## 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
poetry install

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 AWS 자격증명 입력
```

### 2. 로컬 인프라 시작

```bash
# MySQL, DynamoDB Local, MinIO 시작
docker-compose up -d

# DynamoDB 테이블 생성
poetry run python init_dynamodb.py
```

### 3. DB 마이그레이션

```bash
# 마이그레이션 실행
poetry run alembic upgrade head
```

### 4. 서버 시작

```bash
poetry run uvicorn app.main:app --reload
```

### 5. 파이프라인 테스트

```bash
# 전체 파이프라인 테스트 (채팅 저장 → 회의 시작/종료 → 회의록 생성)
poetry run python test_pipeline.py

# 직접 회의록 생성 테스트 (DynamoDB 우회)
poetry run python test_pipeline.py direct
```

## API 엔드포인트

### 채팅 (`/chat`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/chat/message` | 채팅 메시지 저장 |
| GET | `/chat/messages/{team_id}/{project_id}` | 채팅 메시지 조회 |

### 회의 (`/ai`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/ai/meeting/start` | 회의 시작 |
| POST | `/ai/meeting/end` | 회의 종료 (회의록 자동 생성) |

### 회의록 (`/ai`)

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/ai/minutes?team_id=1` | 회의록 목록 조회 |
| POST | `/ai/minutes` | 직접 회의록 생성 |
| GET | `/ai/minutes/{report_id}/content` | 회의록 상세 내용 (S3) |

## 환경변수

| 변수 | 설명 | 로컬 | AWS |
|------|------|------|-----|
| `DDB_ENDPOINT_URL` | DynamoDB 엔드포인트 | `http://localhost:8001` | (비워두기) |
| `S3_ENDPOINT_URL` | S3 엔드포인트 | `http://localhost:9000` | (비워두기) |
| `AWS_S3_BUCKET` | S3 버킷명 | 버킷명 | 버킷명 |
| `BEDROCK_MODEL_ID` | Bedrock 모델 ARN | ARN | ARN |

## 회의록 JSON 형식

```json
{
  "date": "2026-01-06",
  "attendees": ["김철수", "이영희", "박민수"],
  "agenda": "스프린트 회의",
  "decisions": ["API 설계 완료", "다음 주 월요일까지 진행상황 공유"],
  "action_items": [
    {"task": "프론트엔드 로그인 페이지 완성", "assignee": "이영희"},
    {"task": "백엔드 회의록 API 구현", "assignee": "박민수"}
  ],
  "summary": "이번 주 목표 설정 및 역할 분담 완료"
}
```
