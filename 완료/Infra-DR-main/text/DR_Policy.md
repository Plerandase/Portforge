# DR 정책 수립

## 1. DR 전략 개요

| 항목 | 내용 |
|------|------|
| **전략** | Warm Standby |
| **Primary Region** | ap-northeast-2 (Seoul) |
| **DR Region** | ap-northeast-1 (Tokyo) |
| **RTO 목표** | 40분 이내 |
| **RPO 목표** | 5초 이내 |
| **전환 방식** | 수동 전환 |
| **도메인** | portforge.org |

### 1.1 팀 구성

| 역할 | 인원 |
|------|------|
| PM | 1명 |
| PL (팀 리더) | 1명 |
| 팀원 | 4명 |
| **총원** | 6명 |

### 1.2 DR 선언 기준

**DR 선언 권한자**: PL (부재 시 PM)

**DR 선언 조건** (아래 중 하나 만족 시):
1. Health Check 실패 + **20분 이상 지속**
2. AWS 공식 장애 공지 (ap-northeast-2 리전)

**RTO 계산**:
```
장애 지속 20분 + DR 전환 15~20분 = 총 35~40분 (RTO 40분 이내)
```

### 1.3 커뮤니케이션 계획

| 단계 | 시점 | 채널 | 담당 | 내용 |
|------|------|------|------|------|
| 장애 인지 | 즉시 | #인프라-알림 (자동) | Bot | Health Check 실패 알림 |
| 장애 확인 | 5분 내 | #인프라-알림 | 인프라 담당 | "장애 확인 중, 원인 파악 중" |
| DR 선언 | 20분 경과 | #general | PL | "DR 전환 시작, 예상 소요 15~20분" |
| 진행 상황 | 10분 간격 | #인프라-알림 | 인프라 담당 | 전환 진행률 |
| 전환 완료 | 완료 시 | #general | PL | "서비스 복구 완료" |
| 사용자 안내 | 완료 후 | 서비스 내 배너 | 관리자 | 재로그인 안내 (비밀번호 재설정) |

### 1.4 외부 연동 Callback URL

| 서비스 | Callback URL | DR 시 변경 |
|--------|--------------|------------|
| Google OAuth | https://portforge.org/auth/callback | ❌ 불필요 |
| Kakao OAuth | https://portforge.org/auth/callback | ❌ 불필요 |
| Slack Webhook | 동일 URL | ❌ 불필요 |

> 도메인 기반이라 DR 전환 시 변경 불필요

---

## 2. 인프라 구성 상세

### 2.1 VPC 구성
| 항목 | Primary (Seoul) | DR (Tokyo) |
|------|-----------------|------------|
| VPC Name | portforge-test-vpc | portforge-dr-vpc |
| VPC CIDR | 10.10.0.0/16 | 10.20.0.0/16 |
| AZ | ap-northeast-2a, 2c | ap-northeast-1a, 1c |
| Public Subnets | 10.10.1.0/24, 10.10.11.0/24 | 10.20.1.0/24, 10.20.11.0/24 |
| Private Subnets | 10.10.2.0/24, 10.10.12.0/24 | 10.20.2.0/24, 10.20.12.0/24 |
| DB Subnets | 10.10.3.0/24, 10.10.13.0/24 | 10.20.3.0/24, 10.20.13.0/24 |
| NAT Gateway | 2개 (AZ별) | 2개 (AZ별) |
| Internet Gateway | igw-0d94b9a17c7692b5e | 신규 생성 |

### 2.2 EKS 구성
| 항목 | Primary | DR (Warm Standby) |
|------|---------|-------------------|
| Cluster Name | portforge-cluster | portforge-dr-cluster |
| Version | 1.33 | 1.33 |
| Node Group | eks_ng-2026011903... | portforge-dr-node-group |
| Node 수 | 3대 | 2대 (min: 2, max: 4) |
| Instance Type | t3.large | t3.large |
| Node IPs | 10.10.2.147, 10.10.12.95, 10.10.12.249 | - |

### 2.3 RDS 구성
| 항목 | Primary | DR |
|------|---------|-----|
| Instance ID | portforge-test-rds | portforge-dr-rds-replica |
| Type | Primary | Cross-Region Read Replica |
| Engine | MySQL 8.4.7 | MySQL 8.4.7 |
| Port | 3306 | 3306 |
| Instance Class | db.t3.micro | db.t3.micro |
| Multi-AZ | True ✅ | False (비용 절감) |
| Backup Retention | 7일 | 7일 |
| Backup Window | 18:45-19:15 (UTC) | - |
| Subnet Group | portforge-test-db-subnet-group | portforge-dr-db-subnet-group |

### 2.4 DynamoDB Global Tables
| 테이블 | 상태 | Stream | DR 필요 작업 |
|--------|------|--------|--------------|
| team_chats_ddb | ACTIVE | ⚠️ 미설정 | Stream 활성화 → Global Table |
| chat_rooms_ddb | ACTIVE | ⚠️ 미설정 | Stream 활성화 → Global Table |

### 2.5 S3
| 버킷 | 용도 | DR 버킷 |
|------|------|---------|
| portforge-front | 프론트엔드 정적 파일 | portforge-front-dr (수동 생성) |
| portforge-team | 사용자 파일 업로드 | portforge-team-dr (수동 생성) |
| portforge-log | 로그 저장 | portforge-log-dr (수동 생성) |

### 2.6 Cognito
| 항목 | Primary (Seoul) | DR (Tokyo) |
|------|-----------------|------------|
| User Pool ID | ap-northeast-2_4DwI5MdtT | 수동 생성 |
| User Pool Name | User pool - p1jugj | User pool - dr |
| App Client ID | 1lll548h0fo0blhnerb3n1s31d | 수동 생성 |
| App Client Name | Local-test | Local-test-dr |
| OAuth | Google 연동 | Google OAuth 동일 설정 |
| 동기화 | - | Lambda Post Confirmation (수동 설정) |

### 2.7 ECR Repositories
| Repository | Primary URI | DR 필요 작업 |
|------------|-------------|--------------|
| auth-service | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/auth-service | Tokyo ECR 복제 |
| team-service | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/team-service | Tokyo ECR 복제 |
| support-service | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/support-service | Tokyo ECR 복제 |
| project-service | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/project-service | Tokyo ECR 복제 |
| ai-service | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/ai-service | Tokyo ECR 복제 |
| slack-monitoring-bot | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/slack-monitoring-bot | Tokyo ECR 복제 |
| infra-bot | 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/infra-bot | Tokyo ECR 복제 |

### 2.8 Secrets Manager
| Secret Name | 용도 | DR 복제 방식 |
|-------------|------|--------------|
| portforge/ai-service/rds | AI Service DB 접속 | Cross-Region Replication |
| portforge/slack-bot/tokens | Slack Bot 토큰 | Cross-Region Replication |
| portforge/aws/bedrock-credentials | Bedrock 인증 | Cross-Region Replication |
| portforge/slack-bot/all-secrets | Slack Bot 전체 | Cross-Region Replication |

> Secrets Manager는 AWS 콘솔에서 "Replicate secret to other regions" 기능으로 Tokyo 리전에 자동 복제 가능

### 2.9 CloudFront
| Distribution ID | Origin | 설정 | DR 필요 작업 |
|-----------------|--------|------|--------------|
| E1JEYSERFZFFZU | portforge-front.s3.ap-northeast-2.amazonaws.com | redirect-to-https | Origin Failover 설정 |

### 2.10 ALB
| Name | Type | Scheme | DR 필요 작업 |
|------|------|--------|--------------|
| k8s-portforgeapi-19c6a81f3a | application | internet-facing | Tokyo EKS Ingress로 자동 생성 |
| k8s-default-infrabot-d586e69ef7 | application | internet-facing | Tokyo EKS Ingress로 자동 생성 |

### 2.11 Route 53
| 레코드 | 타입 | 대상 | DR 필요 작업 |
|--------|------|------|--------------|
| portforge.org | A (Alias) | CloudFront | Origin Failover |
| api.portforge.org | A (Alias) | k8s ALB | Failover Policy 설정 |
| argocd.portforge.org | A (Alias) | k8s ALB | Failover Policy 설정 |
| grafana.portforge.org | A (Alias) | k8s ALB | Failover Policy 설정 |
| infra-bot.portforge.org | CNAME | k8s ALB | Failover Policy 설정 |

### 2.12 ACM (SSL 인증서)
| Domain | Region | DR 필요 작업 |
|--------|--------|--------------|
| *.portforge.org | ap-northeast-2 | Tokyo에 인증서 발급 |

### 2.13 KMS
| Alias | 용도 | DR 필요 작업 |
|-------|------|--------------|
| alias/eks/portforge-cluster | EKS 암호화 | Tokyo KMS Key 생성 |
| alias/aws/rds | RDS 암호화 | 자동 생성 |
| alias/aws/secretsmanager | Secrets 암호화 | 자동 생성 |
| alias/aws/dynamodb | DynamoDB 암호화 | 자동 생성 |

### 2.14 IAM Roles
| Role Name | 용도 | DR 필요 작업 |
|-----------|------|--------------|
| portforge-cluster-cluster-202601... | EKS Cluster Role | Tokyo Role 생성 |
| eks_ng-eks-node-group-202601... | EKS Node Role | Tokyo Role 생성 |
| portforge-test-lb-controller | ALB Controller | Tokyo Role 생성 |
| portforge-ai-ec2-role | AI Service EC2 | Tokyo Role 생성 |
| eksctl-portforge-cluster-addon-... | Service Account Role | Tokyo Role 생성 |

---

## 3. EKS Workloads

### 3.1 애플리케이션 서비스
| 서비스 | Replicas | Port | DR 필요 작업 |
|--------|----------|------|--------------|
| auth-deployment | 2 | 8000 | K8s manifests 배포 |
| project-service | 2 | 8001 | K8s manifests 배포 |
| team-service | 2 | 8002 | K8s manifests 배포 |
| ai-service | 2 | 8003 | K8s manifests 배포 |
| support-deployment | 1 | 8004 | K8s manifests 배포 |
| infra-bot | 2 | 80 | K8s manifests 배포 |
| slack-monitoring-bot | 1 | - | K8s manifests 배포 |

### 3.2 인프라 서비스
| 서비스 | Namespace | Replicas | DR 필요 작업 |
|--------|-----------|----------|--------------|
| argocd-server | default | 1 | Tokyo ArgoCD 설치 |
| argocd-repo-server | default | 1 | Tokyo ArgoCD 설치 |
| argocd-applicationset-controller | default | 1 | Tokyo ArgoCD 설치 |
| argocd-dex-server | default | 1 | Tokyo ArgoCD 설치 |
| argocd-redis | default | 1 | Tokyo ArgoCD 설치 |
| argocd-notifications-controller | default | 1 | Tokyo ArgoCD 설치 |
| prometheus | default | 1 | Tokyo 모니터링 설치 |
| alertmanager | default | 1 | Tokyo 모니터링 설치 |
| grafana | default | 1 | Tokyo 모니터링 설치 |
| loki | default | 1 | Tokyo 로깅 설치 |
| promtail | default | 3 (DaemonSet) | Tokyo 로깅 설치 |

### 3.3 시스템 서비스
| 서비스 | Namespace | DR 필요 작업 |
|--------|-----------|--------------|
| aws-load-balancer-controller | kube-system | Helm 설치 |
| csi-secrets-store | kube-system | Helm 설치 |
| csi-secrets-store-provider-aws | kube-system | Helm 설치 |
| ebs-csi-controller | kube-system | EKS Addon |
| metrics-server | kube-system | EKS Addon |
| coredns | kube-system | EKS 기본 제공 |
| kube-proxy | kube-system | EKS 기본 제공 |
| aws-node (VPC CNI) | kube-system | EKS 기본 제공 |

### 3.4 Ingress
| Name | Host | Service | DR 필요 작업 |
|------|------|---------|--------------|
| auth-service-ingress | * | auth-service:8000 | Tokyo Ingress 배포 |
| project-service-ingress | * | project-service:8001 | Tokyo Ingress 배포 |
| team-service-ingress | * | team-service:8002 | Tokyo Ingress 배포 |
| ai-ingress | * | ai-service:8003 | Tokyo Ingress 배포 |
| support-ingress | * | support-service:8004 | Tokyo Ingress 배포 |
| argocd-server-ingress | argocd.portforge.org | argocd-server:80 | Tokyo Ingress 배포 |
| grafana-ingress | grafana.portforge.org | grafana:80 | Tokyo Ingress 배포 |
| infra-bot-ingress | infra-bot.portforge.org | infra-bot-service:80 | Tokyo Ingress 배포 |

### 3.5 ConfigMaps
| Name | 용도 | DR 필요 작업 |
|------|------|--------------|
| auth-service-config | Auth 서비스 환경변수 | Tokyo용 ConfigMap 생성 |
| project-service-config | Project 서비스 환경변수 | Tokyo용 ConfigMap 생성 |
| team-service-config | Team 서비스 환경변수 | Tokyo용 ConfigMap 생성 |
| ai-service-config | AI 서비스 환경변수 | Tokyo용 ConfigMap 생성 |
| support-config | Support 서비스 환경변수 | Tokyo용 ConfigMap 생성 |
| infrabot-config | Infra Bot 환경변수 | Tokyo용 ConfigMap 생성 |
| slack-bot-config | Slack Bot 환경변수 | Tokyo용 ConfigMap 생성 |
| argocd-cm | ArgoCD 설정 | Tokyo ArgoCD 설치 시 생성 |
| argocd-notifications-cm | ArgoCD 알림 설정 | Tokyo용 설정 |

---

## 4. RTO/RPO 정의

### RTO (Recovery Time Objective)
| 단계 | 소요 시간 | 누적 |
|------|-----------|------|
| 장애 지속 및 DR 선언 결정 | 20분 | 20분 |
| RDS Read Replica Promote | 5~10분 | 30분 |
| DNS 전파 | 1~5분 | 35분 |
| 서비스 확인 | 5분 | 40분 |
| **예상 총 RTO** | **35~40분** | - |
| **목표 RTO** | **40분 이내** | ✅ |

### RPO (Recovery Point Objective)
| 서비스 | 복제 방식 | RPO |
|--------|-----------|-----|
| RDS (MySQL 8.4.7) | Cross-Region Read Replica | ~5초 |
| DynamoDB | Global Tables | ~1초 |
| S3 | Cross-Region Replication | ~15분 |
| Cognito | Lambda 동기화 | 실시간 (비밀번호 제외) |

---

## 5. Failover 정책

### 전환 방식: 수동 전환

Route 53 Health Check는 **알림용**으로만 사용하고, DR 전환은 **수동**으로 진행합니다.

**이유**:
- 일시적 장애에 자동 전환되는 리스크 방지
- 전환 후 복귀가 복잡함 (RDS Promote 등)
- 포트폴리오 프로젝트 특성상 24시간 모니터링 어려움

### Health Check 설정 (알림용)
| 설정 | 값 |
|------|-----|
| Health Check Path | /health |
| Health Check 간격 | 30초 |
| Failure Threshold | 3회 연속 실패 |
| 알림 | Slack #인프라-알림 |

### 수동 Failover 절차

| 단계 | 작업 | 담당 | 소요시간 |
|------|------|------|----------|
| 1 | DR 선언 (20분 장애 지속 확인) | PL | - |
| 2 | RDS Read Replica Promote | 인프라 담당 | 5~10분 |
| 3 | Route 53 레코드 변경 (Tokyo ALB) | 인프라 담당 | 1~5분 |
| 4 | 서비스 상태 확인 | 인프라 담당 | 5분 |
| 5 | 사용자 안내 (배너/공지) | 관리자 | - |

### 수동 Failover 명령어

```powershell
# 1. RDS Promote
aws rds promote-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1

# 2. Route 53 레코드 변경 (AWS Console 또는 CLI)
# Primary 레코드를 Tokyo ALB로 변경
```

---

## 6. Failback 정책

### 복귀 조건

| 조건 | 기준 |
|------|------|
| Seoul 리전 정상화 | AWS 장애 해제 공지 또는 Health Check 정상 |
| 안정화 확인 | 정상화 후 **30분** 동안 추가 장애 없음 |

### 복귀 시점

- 트래픽 데이터 없으므로 **안정화 확인 후 즉시 복귀**

### 데이터 동기화 (Failback)

DR 중 Tokyo에 쌓인 데이터를 Seoul로 동기화해야 합니다.

| 리소스 | 동기화 방법 |
|--------|-------------|
| RDS | Tokyo → Seoul로 새 Read Replica 생성 후 Promote |
| DynamoDB | Global Table이라 양방향 자동 동기화 ✅ |
| S3 | Tokyo → Seoul CRR 설정 (역방향) |
| Cognito | Lambda 동기화 (역방향 Trigger 추가) |

### Failback 절차

| 단계 | 작업 | 소요 시간 |
|------|------|-----------|
| 1 | Seoul 정상화 확인 | - |
| 2 | 30분 안정화 대기 | 30분 |
| 3 | Tokyo → Seoul 데이터 동기화 | 1~2시간 |
| 4 | Seoul EKS 배포 및 테스트 | 30분 |
| 5 | Route 53 Seoul로 전환 | 5분 |
| 6 | 사용자 안내 (배너/공지) | - |
| 7 | Tokyo DR 상태 복원 (노드 2대로 축소) | 30분 |
| **총 예상 시간** | | **3~4시간** |

### 사용자 안내

| 시점 | 안내 내용 |
|------|-----------|
| DR 전환 시 | "서비스 복구 완료. 비밀번호 재설정 후 로그인해주세요." |
| Failback 시 | "서비스가 정상화되었습니다. 기존 비밀번호로 로그인해주세요." |

> DR 중 Tokyo에서 변경한 비밀번호는 Seoul Cognito에 반영되지 않음

---

## 7. 발견된 문제점 및 해결 방법

| # | 문제 | 심각도 | 해결 방법 |
|---|------|--------|-----------|
| 1 | DynamoDB Stream 미설정 (2개 테이블) | 🔴 높음 | Stream 활성화 → Global Table |
| 2 | Route 53 Health Check 없음 | 🟡 중간 | Terraform으로 설정 |
| 3 | Route 53 Failover Policy 없음 | 🟡 중간 | Terraform으로 설정 |
| 4 | CloudFront Origin Failover 없음 | 🟡 중간 | Console에서 설정 |
| 5 | ECR Cross-Region Replication 없음 | 🟡 중간 | Terraform으로 설정 |

---

## 8. 테스트 정책

### 정기 테스트
| 테스트 유형 | 주기 | 내용 |
|-------------|------|------|
| Health Check 테스트 | 월 1회 | Route 53 Failover 동작 확인 |
| Failover 시뮬레이션 | 분기 1회 | 실제 DR 전환 테스트 |
| Failback 테스트 | 분기 1회 | Seoul 복귀 절차 검증 |
| 데이터 정합성 검증 | 주 1회 | Primary-DR 데이터 비교 |

### 테스트 체크리스트
- [ ] Route 53 Health Check 정상 동작
- [ ] RDS Read Replica Promote 성공
- [ ] DynamoDB Global Tables 동기화 확인
- [ ] EKS Pod 정상 기동 (portforge-dr-cluster)
- [ ] 애플리케이션 헬스체크 통과 (/health)
- [ ] 사용자 로그인 테스트 (Cognito)
- [ ] api.portforge.org Failover 확인
- [ ] grafana.portforge.org Failover 확인

---

## 9. RACI 매트릭스

| 작업 | PL | PM | 인프라 담당 | Backend | Frontend |
|------|----|----|-------------|---------|----------|
| 장애 감지 | I | I | R | I | I |
| DR 선언 결정 | A/R | C | C | I | I |
| DR 전환 실행 | I | I | R | I | I |
| 서비스 검증 | I | I | A | R | R |
| 사용자 공지 | A | R | I | I | I |
| Failback 계획 | A | C | R | C | I |
| Failback 실행 | I | I | R | I | I |

> R: Responsible (실행), A: Accountable (책임), C: Consulted (협의), I: Informed (통보)

---

## 10. DR 중 모니터링

### 모니터링 환경

| 상황 | 모니터링 도구 | 접근 방법 |
|------|---------------|-----------|
| 평상시 (Seoul) | Prometheus/Grafana/Loki | grafana.portforge.org |
| DR 중 (Tokyo) | CloudWatch Container Insights | AWS Console |

### 모니터링 대상 및 임계값

| 카테고리 | 메트릭 | 임계값 | 심각도 |
|----------|--------|--------|--------|
| **EKS** | Node CPU | > 80% | Warning |
| | Node Memory | > 80% | Warning |
| | Pod Restart Count | > 3회/5분 | Critical |
| **RDS** | CPU Utilization | > 80% | Warning |
| | Database Connections | > 80% of max | Warning |
| | Replica Lag | > 60초 | Critical |
| **DynamoDB** | Read/Write Throttle | > 0 | Warning |
| **ALB** | 5xx Error Rate | > 1% | Critical |
| | Response Time | > 3초 | Warning |

### CloudWatch Dashboard 구성

| 위젯 | 메트릭 |
|------|--------|
| EKS Overview | Node CPU, Memory, Pod Count |
| RDS Status | CPU, Connections, Replica Lag |
| DynamoDB | Read/Write Capacity, Throttle |
| ALB | Request Count, Latency, Error Rate |
| Service Health | 각 서비스 Pod 상태 |

### 알람 설정

| 알람 | 조건 | 심각도 | 알림 채널 |
|------|------|--------|-----------|
| EKS-Node-CPU-High | CPU > 80%, 5분 지속 | Warning | #인프라-알림 |
| EKS-Pod-CrashLoop | Restart > 3회/5분 | Critical | #인프라-알림 |
| RDS-CPU-High | CPU > 80%, 5분 지속 | Warning | #인프라-알림 |
| RDS-ReplicaLag-High | Lag > 60초 | Critical | #인프라-알림 |
| ALB-5xx-High | 5xx > 1%, 5분 지속 | Critical | #인프라-알림 |

### 알림 경로

| 상황 | 알림 경로 |
|------|-----------|
| 평상시 | Grafana Alert → Slack #인프라-알림 |
| DR 중 | CloudWatch Alarm → SNS → Lambda → Slack #인프라-알림 |

> 동일한 Slack 채널로 알림이 오므로 운영자 입장에서 동일하게 모니터링 가능

---

## 11. 비용 정책

### 월간 DR 비용
| 항목 | 사양 | 월 비용 |
|------|------|---------|
| EKS Cluster | 1.33 | $73 |
| EKS Nodes | t3.large x 2 | 포함 |
| RDS Read Replica | db.t3.micro, Single-AZ | $15 |
| NAT Gateway | 2개 (AZ별) | $65 |
| S3 복제 | 3개 버킷 CRR | $5 |
| DynamoDB | Global Tables (2개) | $10 |
| 기타 (EIP, 데이터 전송) | - | $36 |
| **총 DR 비용** | | **~$204/월** |

---

## 12. 주요 명령어

### kubectl 설정
```bash
# Primary (Seoul)
aws eks update-kubeconfig --region ap-northeast-2 --name portforge-cluster

# DR (Tokyo)
aws eks update-kubeconfig --region ap-northeast-1 --name portforge-dr-cluster
```

### RDS Promote
```bash
aws rds promote-read-replica \
  --db-instance-identifier portforge-dr-rds-replica \
  --region ap-northeast-1
```

### ECR 로그인
```bash
# Primary (Seoul)
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  023490709500.dkr.ecr.ap-northeast-2.amazonaws.com

# DR (Tokyo)
aws ecr get-login-password --region ap-northeast-1 | \
  docker login --username AWS --password-stdin \
  023490709500.dkr.ecr.ap-northeast-1.amazonaws.com
```

### DynamoDB 테이블 확인
```bash
aws dynamodb describe-table --table-name team_chats_ddb --region ap-northeast-1
aws dynamodb describe-table --table-name chat_rooms_ddb --region ap-northeast-1
```

---

## 13. 문서 관리

| 문서 | 위치 | 업데이트 주기 |
|------|------|---------------|
| DR 정책 | text/DR_Policy.md | 분기 1회 |
| DR 전략 선택 이유 | text/DR_Strategy_Selection.md | 변경 시 |
| DR 구성 가이드 | text/DR_Setup_Guide.md | 변경 시 |
| DR 수동 설정 가이드 | text/DR_Manual_Setup.md | 변경 시 |
| 인프라 코드 | Infra-DR/*.tf | 변경 시 |
