# Primary vs DR 인프라 구성 방식 비교

## 1. 요약

| 구분 | Primary (Seoul) | DR (Tokyo) |
|------|-----------------|------------|
| Terraform 파일 수 | 8개 | 12개 |
| 자동화 수준 | 기본 | 확장 |
| 주석/문서화 | 최소 | 상세 |

---

## 2. 상세 비교표

### 2.1 네트워크 (VPC)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| VPC | ✅ Terraform | ✅ Terraform | 동일 |
| Internet Gateway | ✅ Terraform | ✅ Terraform | 동일 |
| Public Subnets (2개) | ✅ Terraform | ✅ Terraform | 동일 |
| Private Subnets (2개) | ✅ Terraform | ✅ Terraform | 동일 |
| DB Subnets (2개) | ✅ Terraform | ✅ Terraform | 동일 |
| NAT Gateway (2개) | ✅ Terraform | ✅ Terraform | 동일 |
| Route Tables | ✅ Terraform | ✅ Terraform | 동일 |
| Security Groups | ✅ Terraform | ✅ Terraform | 동일 |

### 2.2 컴퓨팅 (EKS)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| EKS Cluster | ✅ Terraform | ✅ Terraform | 동일 |
| Managed Node Group | ✅ Terraform | ✅ Terraform | DR은 축소 운영 |
| IRSA | ✅ Terraform | ✅ Terraform | 동일 |
| Access Entries | ✅ Terraform | ✅ Terraform | 동일 |

### 2.3 데이터베이스 (RDS)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| RDS Instance | ✅ Terraform | ✅ Terraform | DR은 Read Replica |
| DB Subnet Group | ✅ Terraform | ✅ Terraform | 동일 |
| DB Security Group | ✅ Terraform | ✅ Terraform | 동일 |

### 2.4 DynamoDB

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| team_chats_ddb 테이블 | ✅ Terraform | 🔶 Data Source | DR은 참조만 |
| chat_rooms_ddb 테이블 | ✅ Terraform | 🔶 Data Source | DR은 참조만 |
| Global Table 설정 | ❌ 없음 | 📝 수동 가이드 | AWS CLI로 수동 설정 |
| Stream 활성화 | ❌ 없음 | 📝 수동 가이드 | AWS CLI로 수동 설정 |

### 2.5 스토리지 (S3)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| portforge-front | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| portforge-team | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| portforge-log | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| Cross-Region Replication | - | 📝 수동 (Console) | DR만 해당 |

### 2.6 컨테이너 레지스트리 (ECR)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| ECR Repositories | 📝 수동 (Console) | ✅ Terraform | DR만 자동화 |
| Lifecycle Policy | 📝 수동 | ✅ Terraform | DR만 자동화 |
| Replication Config | - | ✅ Terraform | DR만 해당 |

### 2.7 인증 (Cognito)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| User Pool | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| App Client | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| OAuth 설정 | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| Lambda Trigger | - | 📝 수동 | DR 동기화용 |

### 2.8 DNS (Route 53)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| Hosted Zone | 📝 수동 (Console) | 🔶 Data Source | 기존 Zone 참조 |
| A Records | 📝 수동 (Console) | ✅ Terraform | DR만 자동화 |
| Health Check | ❌ 없음 | ✅ Terraform | DR만 해당 |
| Failover Policy | ❌ 없음 | ✅ Terraform | DR만 해당 |

### 2.9 CDN (CloudFront)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| Distribution | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| Origin Failover | - | 📝 수동 (Console) | DR만 해당 |

### 2.10 SSL 인증서 (ACM)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| *.portforge.org | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |

### 2.11 보안 (Secrets Manager)

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| Secrets 생성 | 📝 수동 (Console) | 📝 수동 (Console) | 둘 다 수동 |
| Cross-Region Replication | - | 📝 수동 (Console) | DR만 해당 |

### 2.12 IAM

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| LB Controller Role | ✅ Terraform | ✅ Terraform | 동일 |
| EBS CSI Role | ❌ 없음 | ✅ Terraform | DR만 자동화 |
| ArgoCD Role | ❌ 없음 | ✅ Terraform | DR만 자동화 |
| AI Service Role | ❌ 없음 | ✅ Terraform | DR만 자동화 |

### 2.13 Helm Charts

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| AWS LB Controller | ✅ Terraform | ✅ Terraform | 동일 |
| ArgoCD | ❌ 없음 | ✅ Terraform | DR만 자동화 |
| EBS CSI Driver | ❌ 없음 | ✅ Terraform | DR만 자동화 |

### 2.14 모니터링/알림

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| Prometheus | 📝 수동 (Helm) | 📝 수동 (Helm) | 둘 다 수동 |
| Grafana | 📝 수동 (Helm) | 📝 수동 (Helm) | 둘 다 수동 |
| Loki | 📝 수동 (Helm) | 📝 수동 (Helm) | 둘 다 수동 |
| AlertManager | 📝 수동 (Helm) | 📝 수동 (Helm) | 둘 다 수동 |
| CloudWatch Alarm | 📝 수동 (Console) | ✅ Terraform | DR만 자동화 |

### 2.15 CI/CD

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| GitHub Actions | 📝 수동 (.github) | 📝 수동 (.github) | 코드 레포에 있음 |
| ArgoCD Applications | 📝 수동 (k8s/) | 📝 수동 (k8s/) | K8s manifests |

### 2.16 Slack Bot

| 리소스 | Primary | DR | 비고 |
|--------|---------|-----|------|
| infra-bot | 📝 수동 (k8s/) | 📝 수동 (k8s/) | K8s manifests |
| slack-monitoring-bot | 📝 수동 (k8s/) | 📝 수동 (k8s/) | K8s manifests |

---

## 3. 범례

| 기호 | 의미 |
|------|------|
| ✅ Terraform | Terraform으로 자동화됨 |
| 🔶 Data Source | Terraform Data Source로 참조만 함 |
| 📝 수동 | AWS Console 또는 CLI로 수동 설정 |
| ❌ 없음 | 해당 리소스 없음 |

---

## 4. 주요 차이점 요약

### DR에서 추가된 Terraform 자동화
1. **ECR** - 리포지토리 생성 + Replication 설정
2. **Route 53** - Health Check + Failover Policy
3. **IAM** - EBS CSI, ArgoCD, AI Service Role
4. **Helm** - ArgoCD, EBS CSI Driver
5. **CloudWatch** - Health Check Alarm

### 둘 다 수동인 리소스
1. **S3** - 버킷 생성, Versioning, CRR
2. **Cognito** - User Pool, App Client, OAuth
3. **CloudFront** - Distribution, Origin Failover
4. **ACM** - SSL 인증서
5. **Secrets Manager** - Secrets 생성, Replication
6. **모니터링** - Prometheus, Grafana, Loki
7. **Slack Bot** - K8s manifests로 배포

### Primary에만 있는 Terraform
1. **DynamoDB 테이블 생성** - DR은 Global Table로 자동 복제

---

## 5. 권장 사항

### Primary 업그레이드 시 추가할 것
1. ECR Terraform 코드 추가
2. IAM Role 추가 (EBS CSI, ArgoCD 등)
3. Helm Chart 추가 (ArgoCD, EBS CSI)
4. 주석 및 문서화 강화

### 향후 자동화 고려 대상
1. S3 버킷 생성 + CRR
2. Cognito User Pool
3. CloudFront Distribution
4. ACM 인증서
5. Secrets Manager
