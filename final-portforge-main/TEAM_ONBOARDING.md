# Portforge 팀 온보딩 가이드

## 신규 팀원 - 원클릭 설치

### 1. 사전 설치 (필수)
| 프로그램 | 버전 | 다운로드 |
|---------|------|----------|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| Docker Desktop | 최신 | https://www.docker.com/products/docker-desktop/ |

### 2. 설치 및 실행
```bash
# 1. 프로젝트 클론
git clone https://github.com/csejh1/Portforge.git
cd Portforge

# 2. 원클릭 설치 (환경설정 + 의존성 + DB 초기화)
.\setup.bat

# 3. 서비스 시작 (setup.bat 마지막에 Y 입력하면 자동 실행)
.\start_services.bat
```

### 3. Cognito 설정 (중요!)
회원가입/로그인이 작동하려면 `Auth/.env`에 Cognito 값 설정 필요:
```
COGNITO_USERPOOL_ID=ap-northeast-2_XXXXXXX
COGNITO_APP_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
```
→ 팀장에게 값을 받아서 입력하세요.

### 4. 접속
- 프론트엔드: http://localhost:3000
- API 문서: http://localhost:8000/docs (Auth), 8001 (Project), 8002 (Team), 8003 (AI), 8004 (Support)

---

## 기존 팀원 - 코드 업데이트

```bash
git stash           # 로컬 변경사항 임시 저장
git pull origin main
git stash pop       # 변경사항 복원
.\start_services.bat
```

DB 스키마 변경 시:
```bash
python db_manager.py reset-seed --no-confirm
```

---

## 문제 해결

### Docker 관련 오류
```bash
docker compose down -v   # 컨테이너 완전 삭제
.\setup.bat              # 재설치
```

### Poetry 오류
```bash
# 특정 서비스 venv 재생성
cd Auth
rmdir /s /q .venv
poetry install --no-root
cd ..
```

### 서비스 포트 충돌
이미 사용 중인 포트가 있으면 해당 프로세스 종료:
```bash
netstat -ano | findstr :8000
taskkill /PID [PID번호] /F
```

---

## 서비스 구조

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend | 3000 | React + Vite |
| Auth | 8000 | 인증/사용자 관리 (Cognito) |
| Project | 8001 | 프로젝트/지원 관리 |
| Team | 8002 | 팀/태스크/회의 관리 |
| AI | 8003 | AI 테스트/회의록 생성 |
| Support | 8004 | 알림/채팅/공지사항 |
| MySQL | 3306 | 데이터베이스 |
| MinIO | 9000 | 파일 스토리지 |
| DynamoDB | 8010 | 채팅 메시지 저장 |
