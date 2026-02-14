# 🤖 Infra-Bot: AI 기반 인프라 모니터링 슬랙봇

EKS 클러스터와 AWS 리소스를 실시간으로 모니터링하고, AI(Claude 3.5 Sonnet)를 활용해 알림을 분석하여 Slack으로 전달하는 봇입니다.

---

## 🏗 아키텍처

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Grafana       │────▶│   Infra-Bot      │────▶│   Slack         │
│   Alertmanager  │     │   (FastAPI)      │     │   Channel       │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ K8s API  │ │ Bedrock  │ │Prometheus│
              │ Server   │ │ (Claude) │ │          │
              └──────────┘ └──────────┘ └──────────┘
```

---

## 🎯 기능 상세

### 1. 서비스 상태 조회 (`/service-status`)

마이크로서비스별 Pod 상태를 조회합니다.

**조회 항목:**
- Deployment 이름 및 Replicas 상태 (Ready/Total)
- 각 Pod별 컨테이너 상태 (Running/Waiting/Terminated)
- 컨테이너 재시작 횟수
- 실행 중인 노드
- 컨테이너 이미지 버전

**동작 방식:**
1. 슬래시 커맨드 입력 시 서비스 선택 버튼 표시
2. 버튼 클릭 시 백그라운드에서 K8s API 조회
3. Slack Block Kit 형식으로 결과 전송

**모니터링 대상 서비스:**
| 서비스 | Deployment |
|--------|------------|
| Auth | auth-deployment |
| AI | ai-service |
| Project | project-service |
| Team | team-service |
| Support | support-deployment |

---

### 2. 클러스터 건강검진 (`/health`)

클러스터 전체 상태를 한눈에 확인합니다.

**조회 항목:**
| 카테고리 | 항목 | 데이터 소스 |
|----------|------|-------------|
| 노드 | Ready/NotReady 개수 | K8s API |
| 리소스 | CPU/Memory 사용률 (%) | Metrics Server |
| Pod | Running/Pending/Error 개수 | K8s API |
| I/O | Disk Read/Write (MB/s) | Prometheus |
| I/O | Network RX/TX (MB/s) | Prometheus |
| 알람 | 활성 알람 목록 (최근 5개) | 내부 캐시 |

**Prometheus 쿼리:**
```promql
# Disk I/O
sum(rate(node_disk_read_bytes_total[5m]))
sum(rate(node_disk_written_bytes_total[5m]))

# Network I/O
sum(rate(node_network_receive_bytes_total[5m]))
sum(rate(node_network_transmit_bytes_total[5m]))
```

---

### 3. 네트워크 점검 (`/net-check`)

마이크로서비스 간 통신 및 AWS 리소스 연결 상태를 점검합니다.

**마이크로서비스 점검:**
- 각 서비스의 Pod Ready 상태
- Deployment와 매칭되는 Service 확인
- Service Endpoints 존재 여부 및 개수

**AWS 리소스 점검:**
| 리소스 | 점검 방법 |
|--------|-----------|
| RDS | TCP 연결 테스트 (socket) |
| S3 | `head_bucket` API 호출 |
| DynamoDB | `describe_table` API 호출 |

**상태 표시:**
- ✅ OK: 정상
- ⚠️ Warning: 설정되지 않음 또는 일부 문제
- ❌ Critical: 연결 실패

---

### 4. 인프라 이벤트 조회 (`/events`)

최근 Kubernetes 이벤트를 조회합니다.

**조회 항목:**
- 최근 10건의 이벤트
- 타임스탬프, Reason, 대상 오브젝트, 메시지

**표시 형식:**
```
TIME                 REASON            TARGET                            MESSAGE
2026-01-24 09:00:00  Pulled            Pod/auth-xxx                      Image pulled
2026-01-24 08:55:00  FailedScheduling  Pod/project-xxx                   Insufficient cpu
```

---

### 5. 서비스 로그 조회 (`/logs`)

서비스별 최근 Pod 로그를 조회합니다.

**조회 항목:**
- 가장 최근에 시작된 Pod 선택
- 최근 20줄 로그 출력
- Deployment 이름, Replicas 상태, Pod 이름 표시

---

### 6. AI 알림 분석 (Webhook)

Grafana 알림 발생 시 AI가 원인을 분석하고 조치 가이드를 제공합니다.

**트리거:** `POST /alert` (Grafana Alertmanager Webhook)

**처리 흐름:**
1. Grafana에서 알림 발생 → Webhook 전송
2. 알림 데이터를 Claude 3.5 Sonnet에 전달
3. AI가 원인 분석 및 조치 가이드 생성
4. Slack으로 분석 결과 전송

**AI 응답 형식:**
```
🚨 [INFRA] NodeNotReady
━━━━━━━━━━━━━━━━━━━━
📌 요약: 워커 노드 1대가 NotReady 상태입니다.
🔍 원인: 노드의 kubelet이 응답하지 않거나 네트워크 문제 발생 가능
🔧 조치: `kubectl describe node <node-name>`
```

**안전 원칙:**
- 위험한 명령어 (delete, scale, reboot 등) 제안 금지
- 조회 명령어만 제안 (get, describe, logs 등)

**알림 해결 시:**
```
✅ [해결됨] NodeNotReady 이슈가 정상화되었습니다.
```

---

### 7. 정기 리포트

설정된 시간에 자동으로 클러스터 상태 리포트를 전송합니다.

**스케줄:**
- 기본: 매일 오전 9시 (KST)
- 환경변수로 시간 조정 가능 (`DAILY_REPORT_HOURS`)

**리포트 내용:**
- 클러스터 건강 상태 전체 (노드, Pod, I/O, 알람)
- AI가 생성한 2~3문장 요약
- 이상 징후 우선 표시

**중복 실행 방지:**
- Kubernetes Lease를 사용한 리더 선출
- 여러 Pod가 있어도 한 번만 전송
- `infra-bot-daily-report` Lease 사용

---

## 🎨 응답 색상 코드

Slack 메시지 좌측에 상태를 나타내는 색상 바가 표시됩니다.

| 색상 | 의미 | 조건 |
|------|------|------|
| 🟢 `#2EB67D` | 정상 | 모든 항목 정상 |
| 🟡 `#ECB22E` | 경고 | Pending Pod 있음, 알람 있음 |
| 🔴 `#E01E5A` | 위험 | Error Pod 있음, NotReady 노드 있음 |

---

## 📁 파일 구조

| 파일 | 설명 |
|------|------|
| `main.py` | FastAPI 애플리케이션 (슬래시 커맨드, Webhook, 스케줄러) |
| `Dockerfile` | 컨테이너 이미지 빌드 (Python 3.9, uvicorn) |
| `requirements.txt` | Python 의존성 (fastapi, boto3, kubernetes 등) |
| `configmap.yaml` | 환경 설정 (채널 ID, AWS 리전, 점검 대상 등) |
| `secret.yaml` | 민감 정보 (Slack Token) |
| `infrabot-deployment.yaml` | Deployment (replicas: 2) 및 Service |
| `service-account.yaml` | ServiceAccount, ClusterRole, ClusterRoleBinding |
| `ingress.yaml` | ALB Ingress (외부 접근용) |
| `deploy-bot.ps1` | 배포 자동화 스크립트 |

---

## ✅ 사전 요구사항

### AWS
- EKS 클러스터
- ECR 리포지토리 (`infra-bot`)
- IAM Role (IRSA 설정)
  - `bedrock:InvokeModel` 권한
  - S3, DynamoDB 접근 권한 (net-check용)

### Kubernetes
- AWS Load Balancer Controller
- Metrics Server (CPU/Memory 조회용)
- Prometheus Stack (I/O 메트릭용)

### Slack
- Slack 앱 생성 및 설정 → [SLACK-SETUP.md](./SLACK-SETUP.md) 참고

---

## 🚀 배포

### 1. 설정 파일 수정

**secret.yaml** - Slack Bot Token:
```yaml
stringData:
  SLACK_TOKEN: "xoxb-your-token-here"
```

**configmap.yaml** - 환경 설정:
```yaml
data:
  SLACK_CHANNEL: "C0A935FLSBH"       # 알림 채널 ID
  AWS_REGION: "us-east-1"            # Bedrock 리전
  AWS_RESOURCE_REGION: "ap-northeast-2"
  K8S_NAMESPACE: "default"
  PROMETHEUS_URL: "http://prom-stack-kube-prometheus-prometheus.default.svc:9090"
  RDS_ENDPOINT: "your-rds-endpoint"
  RDS_PORT: "3306"
  S3_BUCKET: "your-bucket-name"
  DYNAMODB_TABLE: "your-table-name"
  DAILY_REPORT_ENABLED: "true"
  DAILY_REPORT_HOURS: "9"
  DAILY_REPORT_TZ: "Asia/Seoul"
```

### 2. 배포 실행
```powershell
.\deploy-bot.ps1 -Action all
```

### 3. 확인
```bash
kubectl get pods -l app=infra-bot
curl http://infra-bot.portforge.org/health
```

---

## 🔍 트러블슈팅

### Pod 문제
```bash
kubectl get pods -l app=infra-bot
kubectl logs -l app=infra-bot --tail=50
kubectl describe pod -l app=infra-bot
```

### Bedrock 호출 실패
```bash
kubectl describe sa infra-bot-sa
kubectl exec -it <pod-name> -- env | grep AWS
```

### Prometheus 연결 실패
```bash
kubectl get svc -A | grep prometheus
kubectl exec -it <pod> -- curl http://prom-stack-kube-prometheus-prometheus.default.svc:9090/-/healthy
```

### 정기 리포트 미발송
```bash
# Lease 상태 확인
kubectl get lease infra-bot-daily-report -o yaml

# 환경변수 확인
kubectl exec <pod> -- env | grep DAILY
```

---

## 📚 관련 문서
- [SLACK-SETUP.md](./SLACK-SETUP.md) - Slack 앱 설정 가이드
