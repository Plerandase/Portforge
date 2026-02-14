# Slack 모니터링 봇 (AWS Secret Manager 연동)

MSA 서비스 모니터링 및 AI 기반 에러 분석을 위한 Slack 봇입니다. AWS Secret Manager를 통해 민감한 정보를 안전하게 관리합니다.

## 🔐 보안 특징

- **AWS Secret Manager 연동**: 토큰과 자격증명을 안전하게 저장
- **환경변수 Fallback**: Secret Manager 실패 시 환경변수로 대체
- **Git 안전**: 민감한 정보가 코드에 노출되지 않음

## 📁 파일 구조

```
Slack/
├── bot.py                    # 봇 메인 코드 (Secret Manager 연동)
├── requirements.txt          # Python 의존성
├── Dockerfile               # Docker 이미지
├── k8s-configmap.yaml       # MSA 서비스 URL 설정
├── k8s-deployment.yaml      # Kubernetes Deployment
├── k8s-rbac.yaml           # RBAC 권한 설정
├── deploy-to-ecr.ps1        # ECR 배포 스크립트
├── deploy-to-k8s.ps1        # EKS 배포 스크립트
├── create-secrets.sh        # Secret Manager 생성 스크립트
├── create-secrets-direct.ps1 # Secret Manager 생성 (PowerShell)
└── README.md                # 이 파일
```

---

## 🚀 배포 가이드

### 전제 조건

1. **AWS CLI 설치 및 설정**
2. **kubectl 설치 및 EKS 클러스터 연결**
3. **Docker 설치**
4. **Slack 앱 생성 및 토큰 발급**

### Step 1: AWS Secret Manager에 시크릿 생성

```bash
aws secretsmanager create-secret \
    --name "portforge/slack-bot/all-secrets" \
    --description "All PortForge Slack Bot secrets" \
    --secret-string '{"SLACK_BOT_TOKEN":"your-bot-token","SLACK_APP_TOKEN":"your-app-token","AWS_ACCESS_KEY_ID":"your-access-key","AWS_SECRET_ACCESS_KEY":"your-secret-key"}' \
    --region ap-northeast-2
```

### Step 2: Docker 이미지 빌드 & ECR 푸시

```bash
cd Slack && \
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com && \
docker build -t slack-monitoring-bot . && \
docker tag slack-monitoring-bot:latest 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/slack-monitoring-bot:latest && \
docker push 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/slack-monitoring-bot:latest
```

### Step 3: Kubernetes 리소스 배포

```bash
# ConfigMap 적용
kubectl apply -f k8s-configmap.yaml

# RBAC 적용
kubectl apply -f k8s-rbac.yaml

# Deployment 적용
kubectl apply -f k8s-deployment.yaml
```

### Step 4: 배포 확인

```bash
# Pod 상태 확인
kubectl get pods -l app=slack-monitoring-bot

# 로그 확인 (Secret Manager 연동 확인)
kubectl logs -l app=slack-monitoring-bot --tail=20
```

---

## 🔧 내부 로직

### Secret Manager 연동 방식

```python
def get_secrets():
    try:
        client = boto3.client('secretsmanager', region_name='ap-northeast-2')
        response = client.get_secret_value(SecretId='portforge/slack-bot/all-secrets')
        secrets = json.loads(response['SecretString'])
        logger.info("✅ AWS Secret Manager에서 시크릿 로드 완료")
        return secrets
    except Exception as e:
        logger.error(f"❌ Secret Manager 에러: {e}")
        # 환경변수 fallback
        return {
            'SLACK_BOT_TOKEN': os.environ.get("SLACK_BOT_TOKEN"),
            'SLACK_APP_TOKEN': os.environ.get("SLACK_APP_TOKEN"),
            'AWS_ACCESS_KEY_ID': os.environ.get("AWS_ACCESS_KEY_ID"),
            'AWS_SECRET_ACCESS_KEY': os.environ.get("AWS_SECRET_ACCESS_KEY")
        }
```

### 모니터링 기능

1. **헬스체크**: 1분마다 MSA 서비스 상태 확인
2. **리소스 모니터링**: 5분마다 CPU/메모리 사용률 체크
3. **AI 에러 분석**: AWS Bedrock Claude를 활용한 스마트 진단
4. **실시간 알림**: Slack 채널로 즉시 알림

---

## ⚠️ 주의사항

### 1. AWS 권한 설정

Pod가 Secret Manager에 접근하려면 다음 권한이 필요합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:portforge/slack-bot/all-secrets*"
        }
    ]
}
```

### 2. 네트워크 설정

- Pod에서 AWS Secret Manager API 호출 가능해야 함
- 인터넷 연결 또는 VPC Endpoint 필요

### 3. 장애 대응

**Secret Manager 연결 실패 시:**
- 환경변수 fallback 동작
- 로그에서 `❌ Secret Manager 에러` 확인 가능

**권한 문제 시:**
- IAM 역할 및 정책 확인
- ServiceAccount 설정 확인

### 4. 보안 고려사항

- Secret Manager 값 변경 시 Pod 재시작 필요
- 로그에 민감한 정보 노출 방지
- Secret Manager 접근 로그 모니터링 권장

---

## 🔍 트러블슈팅

### Pod가 시작되지 않는 경우

```bash
# Pod 상태 확인
kubectl describe pods -l app=slack-monitoring-bot

# 로그 확인
kubectl logs -l app=slack-monitoring-bot
```

### Secret Manager 연결 실패

```bash
# Pod 내부에서 테스트
kubectl exec -it <pod-name> -- python3 -c "
import boto3
client = boto3.client('secretsmanager', region_name='ap-northeast-2')
response = client.get_secret_value(SecretId='portforge/slack-bot/all-secrets')
print('연결 성공!')
"
```

### 봇이 응답하지 않는 경우

1. Slack 토큰 유효성 확인
2. Socket Mode 설정 확인
3. 채널에 봇 초대 여부 확인

---

## 📊 모니터링 명령어

### 실시간 로그 모니터링
```bash
kubectl logs -l app=slack-monitoring-bot -f
```

### 리소스 사용량 확인
```bash
kubectl top pods -l app=slack-monitoring-bot
```

### Secret Manager 값 확인
```bash
aws secretsmanager get-secret-value --secret-id "portforge/slack-bot/all-secrets" --region ap-northeast-2
```

---

## 🔄 업데이트 방법

### 코드 변경 후 재배포

```bash
# 1. 이미지 재빌드 및 푸시
cd Slack && docker build -t slack-monitoring-bot . && docker tag slack-monitoring-bot:latest 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/slack-monitoring-bot:latest && docker push 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/slack-monitoring-bot:latest

# 2. Pod 재시작
kubectl rollout restart deployment/slack-monitoring-bot
```

### Secret Manager 값 변경

```bash
# Secret 업데이트
aws secretsmanager update-secret --secret-id "portforge/slack-bot/all-secrets" --secret-string '{"SLACK_BOT_TOKEN":"new-token",...}' --region ap-northeast-2

# Pod 재시작 (새로운 값 적용)
kubectl rollout restart deployment/slack-monitoring-bot
```

## 배포 전 준비사항

### 1. Slack 앱 설정

#### Step 1: Slack 앱 생성
1. https://api.slack.com/apps 접속
2. "Create New App" → "From scratch" 선택
3. 앱 이름 입력 (예: PortForge Bot)
4. 워크스페이스 선택

#### Step 2: Socket Mode 활성화
1. **Settings** → **Socket Mode** 페이지로 이동
2. "Enable Socket Mode" 토글 **ON**
3. "App-Level Token" 생성:
   - Token Name: `socket-token` (아무거나)
   - Scope: `connections:write` 선택
   - **Generate** 클릭
   - 🔑 **`xapp-...`로 시작하는 토큰 복사** (SLACK_APP_TOKEN)

#### Step 3: OAuth & Permissions 설정
1. **Features** → **OAuth & Permissions** 페이지로 이동
2. **Bot Token Scopes** 섹션에서 다음 추가:
   - `app_mentions:read` - 봇 멘션 읽기
   - `chat:write` - 메시지 보내기
   - `channels:history` - 채널 메시지 읽기 (선택)
   - `channels:read` - 채널 정보 읽기 (선택)

#### Step 4: Event Subscriptions 설정
1. **Features** → **Event Subscriptions** 페이지로 이동
2. "Enable Events" 토글 **ON**
3. **Subscribe to bot events** 섹션에서 다음 추가:
   - `app_mention` - 봇이 멘션될 때
   - `message.channels` - 채널 메시지 (선택)

#### Step 5: 워크스페이스에 설치
1. **Settings** → **Install App** 페이지로 이동
2. "Install to Workspace" 클릭
3. 권한 승인
4. 🔑 **`xoxb-...`로 시작하는 Bot User OAuth Token 복사** (SLACK_BOT_TOKEN)

#### Step 6: 채널에 봇 추가
Slack 채널에서 다음 명령어 실행:
```
/invite @PortForge Bot
```

### 2. AWS Bedrock 설정 (AI 분석용)

AI 에러 분석을 위해 AWS Bedrock 접근 권한이 필요합니다:

1. **IAM 사용자 생성** (또는 기존 사용자 사용)
2. **Bedrock 권한 추가**:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:InvokeModel"
               ],
               "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
           }
       ]
   }
   ```
3. **Access Key 생성** 후 안전하게 보관

### 3. 필요한 토큰 정리

배포 시 다음 토큰들이 필요합니다:

| 토큰 이름 | 형식 | 어디서 확인 |
|----------|------|------------|
| **SLACK_BOT_TOKEN** | `xoxb-...` | OAuth & Permissions 페이지 |
| **SLACK_APP_TOKEN** | `xapp-...` | Socket Mode 페이지 |
| **AWS_ACCESS_KEY_ID** | `AKIA...` | AWS IAM 콘솔 |
| **AWS_SECRET_ACCESS_KEY** | `...` | AWS IAM 콘솔 |

---

## EKS 배포 방법

### Step 1: ECR에 이미지 푸시

```powershell
cd Slack
.\deploy-to-ecr.ps1
```

**출력 예시:**
```
✅ 배포 완료!
이미지 URI: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/slack-bot:latest
```

### Step 2: k8s-deployment.yaml 이미지 URI 업데이트

`k8s-deployment.yaml` 파일을 열고 `image` 필드를 업데이트:

```yaml
image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/slack-bot:latest
```

### Step 3: EKS에 배포

```powershell
.\deploy-to-k8s.ps1 `
  -Namespace "default" `
  -SlackBotToken "xoxb-your-token" `
  -SlackAppToken "xapp-your-token" `
  -AwsAccessKey "AKIA..." `
  -AwsSecretKey "your-secret-key" `
  -ClusterName "your-eks-cluster-name"
```

**파라미터 설명:**
- `-Namespace`: Kubernetes 네임스페이스 (기본값: default)
- `-SlackBotToken`: Slack Bot User OAuth Token (xoxb-...)
- `-SlackAppToken`: Slack App-Level Token (xapp-...)
- `-AwsAccessKey`: AWS Access Key ID (AI 분석용)
- `-AwsSecretKey`: AWS Secret Access Key (AI 분석용)
- `-ClusterName`: EKS 클러스터 이름

---

## 배포 후 확인

### Pod 상태 확인
```powershell
kubectl get pods -l app=slack-monitoring-bot
```

**정상 출력:**
```
NAME                                   READY   STATUS    RESTARTS   AGE
slack-monitoring-bot-xxxxxxxxxx-xxxxx   1/1     Running   0          1m
```

### 로그 확인
```powershell
kubectl logs -f deployment/slack-monitoring-bot
```

**정상 로그:**
```
⚡️ Slack Monitoring Bot starting in Socket Mode...
✅ Bedrock AI 분석 기능 활성화
Alert Channel: #alerts
Monitoring Services: ['project', 'team', 'ai', 'auth', 'support']
AI Analysis: Enabled (Bedrock)
Scheduler started
```

### Slack에서 테스트
Slack 채널에서:
```
@PortForge Bot 상태
```

**정상 응답:**
```
📊 서비스 상태 리포트 (2026-01-20 15:30:00)

✅ 프로젝트 서비스: healthy
✅ 팀 서비스: healthy
✅ AI 서비스: healthy
```

---

## 사용 방법

### 명령어

| 명령어 | 설명 |
|--------|------|
| `@bot 상태` | 모든 서비스 상태 조회 |
| `@bot status` | 모든 서비스 상태 조회 |
| `@bot 메트릭` | 모든 서비스 메트릭 조회 |
| `@bot metrics` | 모든 서비스 메트릭 조회 |
| `@bot help` | 도움말 표시 |

### 자동 알림 (AI 분석 포함)

봇이 자동으로 다음 상황에서 **AI 분석과 함께** 알림을 보냅니다:

- ⚠️ CPU 사용률 80% 초과
- ⚠️ 메모리 사용률 80% 초과  
- 🔴 서비스 다운
- 🔴 에러율 10% 초과 → **🤖 AI 진단 포함**

**AI 분석 알림 예시:**
```
🚨 인증 서비스 에러 발생 + AI 분석

📊 현재 상황:
• 에러율: 12.5% (임계값: 10%)
• 총 요청: 1,234건
• 메모리: 85%

🔍 문제 엔드포인트:
• /auth/verify-email: 15건 (4xx)
• /auth/refresh-token: 3건 (5xx)

🤖 AI 진단 결과:
1. 즉시 확인사항 (5분 내 체크 가능)
   - kubectl logs deployment/auth-service | grep ERROR
   - DB 커넥션 풀 상태 확인

2. 가능한 원인 (메트릭 기반 추론)
   - JWT 토큰 만료 처리 로직 오류
   - 데이터베이스 연결 지연 가능성

3. 우선순위별 조치 (심각도 순)
   - 높음: DB 커넥션 풀 크기 증가
   - 중간: 메모리 사용량 모니터링 강화

⏰ 2026-01-21 15:30:25
```

**알림 채널:** `#alerts` (k8s-deployment.yaml에서 변경 가능)

---

## 설정 변경

### 알림 임계값 변경

`k8s-deployment.yaml` 파일에서:

```yaml
env:
- name: CPU_THRESHOLD
  value: "80"  # CPU 임계값 (%)
- name: MEMORY_THRESHOLD
  value: "80"  # 메모리 임계값 (%)
- name: ERROR_RATE_THRESHOLD
  value: "10"  # 에러율 임계값 (%)
```

### 알림 채널 변경

```yaml
env:
- name: ALERT_CHANNEL
  value: "#your-channel"  # 원하는 채널로 변경
```

### 모니터링 주기 변경

`bot.py` 파일에서:

```python
# 1분마다 헬스체크
schedule.every(1).minutes.do(monitor_health)

# 5분마다 리소스 체크
schedule.every(5).minutes.do(monitor_resources)
```

---

## 트러블슈팅

### Pod가 시작되지 않음

```powershell
# Pod 상세 정보 확인
kubectl describe pod -l app=slack-monitoring-bot

# 로그 확인
kubectl logs -l app=slack-monitoring-bot
```

**일반적인 원인:**
- Secret이 없음 → `kubectl get secret slack-bot-secret` 확인
- 이미지 pull 실패 → ECR 권한 확인
- 토큰 오류 → Secret 값 확인

### 봇이 응답하지 않음

1. **Pod 로그 확인:**
   ```powershell
   kubectl logs -f deployment/slack-monitoring-bot
   ```

2. **WebSocket 연결 확인:**
   로그에 "Slack Monitoring Bot starting" 메시지가 있는지 확인

3. **채널에 봇 추가 확인:**
   ```
   /invite @PortForge Bot
   ```

### 알림이 오지 않음

1. **알림 채널 확인:**
   - 봇이 알림 채널에 추가되어 있는지 확인
   - `ALERT_CHANNEL` 환경변수 확인

2. **서비스 연결 확인:**
   ```powershell
   # Pod 내부에서 서비스 연결 테스트
   kubectl exec -it deployment/slack-monitoring-bot -- curl http://project-service:8001/liveness
   ```

---

## 업데이트 방법

코드 변경 후:

```powershell
# 1. 이미지 재빌드 및 푸시
.\deploy-to-ecr.ps1

# 2. Deployment 재시작
kubectl rollout restart deployment/slack-monitoring-bot
```

---

## 주의사항

1. **Socket Mode**: 단일 Pod만 실행 (replicas: 1)
2. **토큰 보안**: Secret을 Git에 커밋하지 마세요
3. **서비스 디스커버리**: MSA 서비스는 Kubernetes Service 이름으로 호출 (예: `http://project-service:8001`)
4. **재시작**: Pod 재시작 시 10-30초 다운타임 발생 (Kubernetes가 자동 재시작)
