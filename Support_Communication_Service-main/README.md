# PortForge 프로젝트 - Support & Communication 서비스

## 1. Support & Communication 서비스 (고객지원 및 커뮤니케이션 서비스)

### 1.1 개요

PortForge Support & Communication 서비스는 플랫폼 내 실시간 채팅, 알림 시스템, 공지사항/배너 관리, 신고 처리 등 사용자 간 커뮤니케이션과 플랫폼 운영을 지원하는 마이크로서비스입니다.

AWS DynamoDB를 활용한 실시간 채팅과 MySQL 기반의 알림/공지 시스템을 통해 팀 협업과 플랫폼 관리 기능을 제공합니다.

### 1.2 핵심 기능

#### 1.2.1 실시간 팀 채팅 시스템

- **WebSocket 기반 실시간 통신**: 프로젝트별 채팅방에서 실시간 메시지 송수신
- **DynamoDB 영구 저장**: 채팅 메시지의 안정적인 저장 및 조회
- **채팅방 관리**: 사용자별 채팅방 목록 및 최근 활동 시간 추적
- **날짜 범위 조회**: 특정 기간의 채팅 로그 조회 지원

**핵심 로직 예시**
```python
@router.websocket("/ws/chat/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: int):
    await websocket.accept()
    connections = chat_connections.setdefault(project_id, set())
    connections.add(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            msg = _build_message(project_id, payload)
            
            # DynamoDB에 메시지 저장
            saved = await save_chat_message(project_id, msg)
            
            # 같은 프로젝트의 모든 연결에 브로드캐스트
            for ws in list(connections):
                await ws.send_json(saved)
    except WebSocketDisconnect:
        connections.discard(websocket)
```

**채팅 메시지 구조**
```json
{
  "message_id": "uuid-string",
  "project_id": 1,
  "user_id": "user-uuid",
  "senderName": "김철수",
  "message": "안녕하세요, 오늘 회의 시작합니다.",
  "timestamp": "2026-01-24T10:30:00Z",
  "created_at": "2026-01-24T10:30:00Z"
}
```

#### 1.2.2 알림 시스템

- **개인화된 알림**: 사용자별 알림 생성 및 관리
- **읽음 상태 관리**: 알림 읽음/안읽음 상태 추적
- **MSA 연동 알림**: 신고 처리, 프로젝트 상태 변경 시 자동 알림 발송
- **딥링크 지원**: 알림 클릭 시 관련 페이지로 이동

**알림 생성 예시**
```python
async def create_notification(user_id: str, message: str, link: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        notif = Notification(
            user_id=user_id,
            message=message,
            link=link,
        )
        session.add(notif)
        await session.commit()
        return {
            "notification_id": notif.notification_id,
            "user_id": notif.user_id,
            "message": notif.message,
            "link": notif.link,
            "is_read": notif.is_read,
            "created_at": notif.created_at,
        }
```

#### 1.2.3 공지사항 및 배너 관리

- **공지사항 CRUD**: 플랫폼 공지사항 생성, 조회, 수정, 삭제
- **배너 관리**: 메인 페이지 배너 관리 (활성화/비활성화)
- **최신 공지 조회**: 프론트엔드 호환용 최신 공지사항 API

**배너 데이터 구조**
```json
{
  "banner_id": 1,
  "title": "신규 기능 출시 안내",
  "link": "https://portforge.com/notice/1",
  "is_active": true,
  "created_at": "2026-01-20T09:00:00Z",
  "updated_at": "2026-01-20T09:00:00Z"
}
```

#### 1.2.4 신고 처리 시스템

- **신고 접수**: 프로젝트/사용자 신고 접수 및 관리
- **관리자 처리**: 경고(warn), 기각(dismiss), 삭제(delete) 처리
- **자동 알림 발송**: 신고 처리 결과를 신고자와 프로젝트 팀장에게 알림
- **MSA 연동 삭제**: 프로젝트 삭제 시 Project Service와 연동

**신고 처리 워크플로우**
```python
@router.patch("/reports/{report_id}")
async def handle_report(report_id: int, payload: ReportDecisionRequest):
    # 1. 신고 상태 업데이트
    updated = await report_service.update_report(report_id, payload.action, payload.note)
    
    # 2. 프로젝트 정보 및 팀장 조회
    project_info = await msa_client.get_project_basic(project_id)
    team_members = await msa_client.get_team_members(team_id)
    leader = next((m for m in members if m.get("role") == "LEADER"), None)
    
    # 3. action="delete"이면 프로젝트 삭제
    if action == "delete":
        await msa_client._make_request("project", f"/projects/{project_id}", "DELETE")
    
    # 4. 신고자와 팀장에게 알림 전송
    await notification_service.create_notification(reporter_id, message)
    await notification_service.create_notification(leader_id, team_message)
```

**신고 상태 (ProjectReportStatus)**
| 상태 | 설명 |
|------|------|
| PENDING | 신고 접수됨 (초기 상태) |
| IN_PROGRESS | 처리 중 (경고 조치) |
| RESOLVED | 해결됨 (삭제 처리) |
| DISMISSED | 기각됨 (무혐의) |

**관리자 액션 → 상태 매핑**
| 액션 | 결과 상태 | 설명 |
|------|----------|------|
| `warn` | IN_PROGRESS | 경고만 주고 지켜보는 상태 |
| `delete` | RESOLVED | 프로젝트 삭제 + 종결 |
| `dismiss` | DISMISSED | 무혐의로 기각 |

**신고 처리 흐름**
```
1. 신고 접수 (PENDING)
        ↓
2. 관리자가 /admin/reports/{id} PATCH 호출
        ↓
3. action에 따라 분기:
   
   [warn]
   - 상태 → IN_PROGRESS
   - 신고자에게: "경고 조치가 취해졌습니다"
   - 팀장에게: "경고 조치가 취해졌습니다"
   
   [delete]
   - 상태 → RESOLVED
   - Project Service에 DELETE 요청 (실제 프로젝트 삭제)
   - 신고자에게: "프로젝트가 삭제되었습니다"
   - 팀장에게: "프로젝트가 삭제되었습니다"
   
   [dismiss]
   - 상태 → DISMISSED
   - 신고자에게: "무혐의로 처리되었습니다"
   - 팀장에게: "무혐의로 처리되었습니다"
```

**참고**: `warn` 후에도 `delete`나 `dismiss`로 변경 가능 (상태 전이 제한 없음). 처리 사유는 `resolution_note`에 기록됨.

#### 1.2.5 이벤트 관리

- **이벤트 CRUD**: 해커톤, 컨퍼런스 등 이벤트 정보 관리
- **카테고리 필터링**: 이벤트 유형별 조회
- **일정 관리**: 이벤트 시작/종료 일자 관리

### 1.3 기술적 특징

#### 1.3.1 하이브리드 데이터베이스 아키텍처

| 데이터 유형 | 저장소 | 선택 이유 |
|------------|--------|----------|
| 채팅 메시지 | DynamoDB | 고속 쓰기, 시계열 데이터 최적화 |
| 채팅방 정보 | DynamoDB | 실시간 업데이트, 유연한 스키마 |
| 알림 | MySQL | 트랜잭션 보장, 복잡한 쿼리 지원 |
| 공지/배너 | MySQL | CRUD 작업, 관계형 데이터 |
| 신고 | MySQL | 상태 관리, 감사 로그 |

#### 1.3.2 WebSocket 연결 관리

```python
# 프로젝트별 WebSocket 연결 관리 (In-Memory)
chat_connections: Dict[int, Set[WebSocket]] = {}

# 연결 시 프로젝트 채팅방에 추가
connections = chat_connections.setdefault(project_id, set())
connections.add(websocket)

# 메시지 브로드캐스트
for ws in list(connections):
    try:
        await ws.send_json(saved)
    except Exception:
        connections.discard(ws)  # 실패한 연결 제거
```

#### 1.3.3 MSA 서비스 간 통신

```python
class MSAClient:
    """MSA 서비스 간 HTTP 통신 클라이언트"""
    
    def __init__(self):
        self.service_urls = {
            "auth": settings.AUTH_SERVICE_URL,
            "project": settings.PROJECT_SERVICE_URL,
            "team": settings.TEAM_SERVICE_URL,
            "ai": settings.AI_SERVICE_URL,
            "support": settings.SUPPORT_SERVICE_URL
        }
    
    async def get_project_basic(self, project_id: int) -> Optional[Dict]:
        return await self._make_request("project", f"/projects/{project_id}/basic")
    
    async def get_team_members(self, team_id: int) -> Optional[List[Dict]]:
        return await self._make_request("team", f"/teams/{team_id}/members")
```

#### 1.3.4 시스템 구조도

```
[Frontend] ←→ [Support Service] ←→ [DynamoDB] (채팅)
                    ↓                    
              [MySQL] (알림/공지/신고)
                    ↓
         [Auth/Project/Team Service] (MSA 연동)
```

### 1.4 데이터 모델

#### 1.4.1 MySQL 테이블

**project_reports (신고)**
```sql
- report_id: BIGINT (PK)
- user_id: VARCHAR(36) (신고자)
- project_id: BIGINT (신고 대상)
- type: ENUM('REPORT', 'INQUIRY', 'BUG')
- content: TEXT
- status: ENUM('PENDING', 'IN_PROGRESS', 'RESOLVED', 'DISMISSED')
- resolution_note: TEXT
- created_at, updated_at: DATETIME
```

**notifications (알림)**
```sql
- notification_id: BIGINT (PK)
- user_id: VARCHAR(36)
- message: TEXT
- link: TEXT
- is_read: BOOLEAN
- created_at, updated_at: DATETIME
```

**notices (공지사항)**
```sql
- notice_id: BIGINT (PK)
- title: VARCHAR(100)
- content: TEXT
- created_at, updated_at: DATETIME
```

**banners (배너)**
```sql
- banner_id: BIGINT (PK)
- title: VARCHAR(100)
- link: TEXT
- is_active: BOOLEAN
- created_at, updated_at: DATETIME
```

#### 1.4.2 DynamoDB 테이블

**team_chats_ddb (채팅 메시지)**
```
- project_id (PK): Number
- timestamp (SK): String (ISO 8601)
- message_id: String
- user_id: String
- message: String
- created_at: String
```

**chat_rooms_ddb (채팅방)**
```
- user_id (PK): String
- room_id: Number
- updated_at: String
```

### 1.5 API 엔드포인트

#### 채팅 API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/chat/{project_id}/messages` | 채팅 메시지 목록 조회 |
| POST | `/chat/{project_id}/messages` | 채팅 메시지 전송 |
| WS | `/ws/chat/{project_id}` | WebSocket 실시간 채팅 |
| POST | `/chat/message` | FE 호환용 메시지 저장 |
| GET | `/chat/messages/{team_id}/{project_id}` | FE 호환용 메시지 조회 |

#### 알림 API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/notifications` | 알림 목록 조회 |
| POST | `/notifications` | 알림 생성 |
| POST | `/notifications/read` | 알림 읽음 처리 |

#### 콘텐츠 API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/notices` | 공지사항 목록 |
| POST | `/notices` | 공지사항 생성 |
| GET | `/notices/latest` | 최신 공지사항 |
| GET | `/banners` | 배너 목록 |
| POST | `/banners` | 배너 생성 |
| PATCH | `/banners/{id}` | 배너 수정 |
| DELETE | `/banners/{id}` | 배너 삭제 |

#### 관리자 API
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/admin/reports` | 신고 목록 조회 |
| PATCH | `/admin/reports/{id}` | 신고 처리 |
| DELETE | `/admin/projects/{id}` | 프로젝트 삭제 |
| GET/POST/PATCH/DELETE | `/admin/banners/*` | 배너 관리 |
| GET/POST/PATCH/DELETE | `/admin/notices/*` | 공지사항 관리 |

### 1.6 성능 지표

| 항목 | 수치 |
|------|------|
| WebSocket 연결 응답 | < 100ms |
| 채팅 메시지 저장 | < 50ms (DynamoDB) |
| 알림 생성 | < 100ms |
| 신고 처리 (MSA 연동 포함) | < 2초 |
| 동시 WebSocket 연결 | 프로젝트당 무제한 (메모리 기반) |

### 1.7 환경 설정

```env
# [App Settings]
PROJECT_NAME=Support-Communication-Service
ENV=local
DEBUG=true

# [Database - MySQL]
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/support_db

# [AWS DynamoDB]
DDB_ENDPOINT_URL=http://localhost:4566
DYNAMODB_TABLE_CHATS=team_chats_ddb
DYNAMODB_TABLE_ROOMS=chat_rooms_ddb

# [MSA Service URLs]
AUTH_SERVICE_URL=http://auth-service
PROJECT_SERVICE_URL=http://project-service
TEAM_SERVICE_URL=http://team-service
AI_SERVICE_URL=http://ai-service
```

---
