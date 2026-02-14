# PortForge DR (Disaster Recovery) Infrastructure

**DR Region**: Tokyo (ap-northeast-1)  
**Primary Region**: Seoul (ap-northeast-2)  
**Strategy**: Warm Standby

---

## 📋 목차

1. [개요](#개요)
2. [DR 전략](#dr-전략)
3. [아키텍처](#아키텍처)
4. [비용 분석](#비용-분석)
5. [사전 요구사항](#사전-요구사항)
6. [배포 가이드](#배포-가이드)
7. [재해 복구 절차](#재해-복구-절차)
8. [테스트 방법](#테스트-방법)
9. [유지보수](#유지보수)
10. [트러블슈팅](#트러블슈팅)

---

## 개요

PortForge 서비스의 재해 복구(DR) 인프라를 Terraform으로 구성합니다.  
Primary Region(Seoul) 장애 시 DR Region(Tokyo)으로 자동 전환하여 서비스 연속성을 보장합니다.

### 주요 목표

- **RTO (Recovery Time Objective)**: 11.5~20.5분
- **RPO (Recovery Point Objective)**: 1~5초
- **가용성**: 99.9% 이상

---

## DR 전략

### Warm Standby 전략

| 구성 요소 | Primary (Seoul) | DR (Tokyo) | 복제 방식 |
|----------|----------------|-----------|----------|
| **VPC** | 10.10.0.0/16 | 10.20.0.0/16 | 독립 |
| **EKS** | 2 nodes (t3.large) | 2 nodes (t3.large) | ArgoCD Multi-cluster |
| **RDS** | Multi-AZ (db.t3.micro) | Single-AZ Read Replica | Cross-Region Replication |
| **DynamoDB** | On-Demand | On-Demand | Global Tables (양방향) |
| **S3** | 3 buckets | 3 buckets (CRR) | Cross-Region Replication |
| **ECR** | 5 repositories | 5 repositories | Cross-Region Replication |
| **Cognito** | Primary 사용 | Primary 사용 | N/A |
| **Bedrock** | Claude Opus 4.5 | Claude Opus 4.5 | N/A |

### 비용

- **Primary Region**: $230/월
- **DR Region**: +$204/월 (+88%)
- **총 비용**: $434/월

---

## 아키텍처

### 평상시 (Normal Operation)

```
사용자
  ↓
Route 53 (Primary)
  ↓
Seoul Region
  ├─ EKS (2 nodes)
  ├─ RDS (Multi-AZ)
  ├─ DynamoDB ←→ Tokyo DynamoDB (실시간 복제)
  └─ S3 → Tokyo S3 (CRR)

Tokyo Region (Standby)
  ├─ EKS (2 nodes, 최소 Pod)
  ├─ RDS (Read Replica)
  ├─ DynamoDB (Global Table)
  └─ S3 (Replica)
```

### 재해 발생 시 (Disaster Recovery)

```
사용자
  ↓
Route 53 (Failover → DR)
  ↓
Tokyo Region (Active)
  ├─ EKS (Scale-out to 4 nodes)
  ├─ RDS (Promote to Primary)
  ├─ DynamoDB (Global Table)
  └─ S3 (Replica)
```

---

## 비용 분석

### Primary Region (Seoul) - 기존

| 서비스 | 사양 | 월 비용 |
|--------|------|---------|
| EKS Control Plane | 1 cluster | $73 |
| EC2 (EKS Nodes) | 2 × t3.large | $62 |
| RDS MySQL | db.t3.micro (Multi-AZ) | $52 |
| DynamoDB | On-Demand | $10 |
| NAT Gateway | 2 × NAT | $65 |
| EIP | 2 × EIP | $7 |
| S3 | 100GB | $3 |
| ECR | 5 repositories | $5 |
| **합계** | | **$277** |

### DR Region (Tokyo) - 추가

| 서비스 | 사양 | 월 비용 |
|--------|------|---------|
| EKS Control Plane | 1 cluster | $73 |
| EC2 (EKS Nodes) | 2 × t3.large | $62 |
| RDS MySQL | db.t3.micro (Single-AZ) | $26 |
| DynamoDB | Global Tables | $10 |
| NAT Gateway | 2 × NAT | $65 |
| EIP | 2 × EIP | $7 |
| S3 CRR | 100GB | $3 |
| ECR | 5 repositories | $5 |
| **합계** | | **$251** |

### 총 비용

- **Primary + DR**: $528/월
- **증가율**: +88%

---

## 사전 요구사항

### 1. 소프트웨어

- Terraform >= 1.0
- AWS CLI >= 2.0
- kubectl >= 1.28
- Helm >= 3.0

### 2. AWS 권한

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "eks:*",
        "rds:*",
        "dynamodb:*",
        "s3:*",
        "ecr:*",
        "iam:*",
        "route53:*",
        "elasticloadbalancing:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Primary Region 리소스

- RDS 인스턴스: `portforge-test-rds`
- DynamoDB 테이블: `team_chats_ddb`, `chat_rooms_ddb`
- S3 버킷: `portforge-team`, `portforge-log`, `portforge-front`
- ECR 리포지토리: `portforge-ai`, `portforge-auth`, `portforge-project`, `portforge-support`, `portforge-team`

---

## 배포 가이드

### 1. 초기 설정

```powershell
# 1. 디렉토리 이동
cd Infra-DR

# 2. Terraform 초기화
terraform init

# 3. 변수 파일 확인 및 수정
# dr.tfvars 파일에서 admin_principal_arns 등 확인
```

### 2. 배포 계획 확인

```powershell
# Dry-run으로 생성될 리소스 확인
terraform plan -var-file="dr.tfvars"
```

### 3. DR 인프라 배포

```powershell
# 전체 배포 (약 20~30분 소요)
terraform apply -var-file="dr.tfvars"

# 또는 특정 리소스만 배포
terraform apply -var-file="dr.tfvars" -target=module.eks_dr
```

### 4. kubectl 설정

```powershell
# DR EKS 클러스터 접근 설정
aws eks update-kubeconfig --region ap-northeast-1 --name portforge-dr-cluster

# 노드 확인
kubectl get nodes

# Pod 확인
kubectl get pods -A
```

### 5. ArgoCD 설정

```powershell
# ArgoCD 서버 주소 확인
kubectl get svc -n argocd argocd-server

# ArgoCD 초기 비밀번호 확인
kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# ArgoCD 로그인
argocd login <ARGOCD_SERVER> --username admin --password <PASSWORD>

# Primary 클러스터 추가 (Multi-cluster)
argocd cluster add portforge-cluster --name primary-seoul
```

### 6. DynamoDB Global Tables 설정

```powershell
# Primary Region에서 Stream 활성화
aws dynamodb update-table `
  --table-name team_chats_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2

# Global Table 생성
aws dynamodb create-global-table `
  --global-table-name team_chats_ddb `
  --replication-group RegionName=ap-northeast-2 RegionName=ap-northeast-1 `
  --region ap-northeast-2

# chat_rooms_ddb도 동일하게 반복
```

### 7. S3 CRR 활성화 확인

```powershell
# Primary 버킷의 Replication 상태 확인
aws s3api get-bucket-replication --bucket portforge-team --region ap-northeast-2

# DR 버킷 확인
aws s3 ls s3://portforge-team-dr --region ap-northeast-1
```

### 8. ECR 이미지 복제

```powershell
# ECR 로그인 (Primary)
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com

# ECR 로그인 (DR)
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 023490709500.dkr.ecr.ap-northeast-1.amazonaws.com

# 이미지 복제 (예시: portforge-ai)
docker pull 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/portforge-ai:latest
docker tag 023490709500.dkr.ecr.ap-northeast-2.amazonaws.com/portforge-ai:latest 023490709500.dkr.ecr.ap-northeast-1.amazonaws.com/portforge-ai:latest
docker push 023490709500.dkr.ecr.ap-northeast-1.amazonaws.com/portforge-ai:latest
```

---

## 재해 복구 절차

### 1. 재해 감지 (자동)

- Route 53 Health Check가 Primary Region 장애 감지 (3회 연속 실패)
- CloudWatch Alarm 발생
- Slack 알림 전송

### 2. RDS Read Replica 승격 (수동)

```powershell
# Read Replica를 Primary로 승격
aws rds promote-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1

# 승격 상태 확인 (약 5~10분 소요)
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].DBInstanceStatus'
```

### 3. EKS 노드 Scale-out (자동/수동)

```powershell
# ArgoCD가 자동으로 Pod 수 증가
# 또는 수동으로 Deployment 수정
kubectl scale deployment <deployment-name> --replicas=2 -n default

# 노드 수 증가 (필요 시)
aws eks update-nodegroup-config `
  --cluster-name portforge-dr-cluster `
  --nodegroup-name dr_node_group `
  --scaling-config desiredSize=4 `
  --region ap-northeast-1
```

### 4. K8s ConfigMap 업데이트

```powershell
# RDS 엔드포인트 업데이트
kubectl edit configmap -n default <service-configmap>

# 변경 사항:
# - DB_HOST: DR RDS 엔드포인트
# - S3_BUCKET: portforge-team-dr
# - ECR_REGISTRY: ap-northeast-1

# Pod 재시작
kubectl rollout restart deployment/<deployment-name> -n default
```

### 5. Route 53 Failover (자동)

- Health Check 실패 시 자동으로 DR Region으로 전환 (30~90초)
- 사용자는 동일한 도메인으로 접속

### 6. 서비스 확인

```powershell
# Pod 상태 확인
kubectl get pods -A

# 서비스 엔드포인트 확인
kubectl get svc -A

# 로그 확인
kubectl logs -f <pod-name> -n default

# Health Check
curl http://<DR_ALB_DNS>/health
```

---

## 테스트 방법

### 1. Failover 테스트

```powershell
# Primary Region의 모든 Pod 중지
kubectl scale deployment --all --replicas=0 -n default --context=primary-seoul

# Route 53 Health Check 상태 확인
aws route53 get-health-check-status --health-check-id <HEALTH_CHECK_ID>

# DNS 조회로 Failover 확인
nslookup <domain_name>
dig <domain_name>

# DR Region에서 서비스 응답 확인
curl http://<domain_name>/health
```

### 2. RDS Replication Lag 확인

```powershell
# Primary RDS
aws rds describe-db-instances `
  --db-instance-identifier portforge-test-rds `
  --region ap-northeast-2 `
  --query 'DBInstances[0].LatestRestorableTime'

# DR Read Replica
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].LatestRestorableTime'
```

### 3. DynamoDB Global Tables 복제 확인

```powershell
# Primary Region에 데이터 삽입
aws dynamodb put-item `
  --table-name team_chats_ddb `
  --item '{"project_id":{"N":"999"},"timestamp":{"S":"2026-01-23T00:00:00Z"},"message":{"S":"DR Test"}}' `
  --region ap-northeast-2

# DR Region에서 데이터 확인 (1~5초 후)
aws dynamodb get-item `
  --table-name team_chats_ddb `
  --key '{"project_id":{"N":"999"},"timestamp":{"S":"2026-01-23T00:00:00Z"}}' `
  --region ap-northeast-1
```

### 4. S3 CRR 확인

```powershell
# Primary 버킷에 파일 업로드
aws s3 cp test.txt s3://portforge-team/test.txt --region ap-northeast-2

# DR 버킷에서 파일 확인 (15분 이내)
aws s3 ls s3://portforge-team-dr/test.txt --region ap-northeast-1
```

---

## 유지보수

### 정기 점검 (월 1회)

1. **RDS Replication Lag 확인**
2. **DynamoDB Global Tables 상태 확인**
3. **S3 CRR 상태 확인**
4. **ECR 이미지 동기화 확인**
5. **Route 53 Health Check 테스트**
6. **DR Region EKS 노드 상태 확인**
7. **비용 분석 및 최적화**

### 백업 정책

- **RDS**: 자동 백업 7일 보관
- **DynamoDB**: Point-in-Time Recovery 활성화
- **S3**: Versioning 활성화

### 모니터링

- **CloudWatch Alarms**: RDS, EKS, DynamoDB
- **Route 53 Health Check**: Primary Region 상태
- **Slack Notifications**: 장애 알림

---

## 트러블슈팅

### 1. RDS Read Replica 생성 실패

**원인**: Primary RDS에 백업이 활성화되지 않음

**해결**:
```powershell
aws rds modify-db-instance `
  --db-instance-identifier portforge-test-rds `
  --backup-retention-period 7 `
  --region ap-northeast-2
```

### 2. DynamoDB Global Tables 생성 실패

**원인**: Stream이 활성화되지 않음

**해결**:
```powershell
aws dynamodb update-table `
  --table-name team_chats_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2
```

### 3. S3 CRR 작동하지 않음

**원인**: Versioning이 비활성화됨

**해결**:
```powershell
aws s3api put-bucket-versioning `
  --bucket portforge-team `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-2
```

### 4. EKS 노드가 시작되지 않음

**원인**: Subnet에 IP 주소 부족

**해결**:
- VPC CIDR 확장
- 또는 불필요한 리소스 삭제

### 5. ArgoCD가 DR 클러스터에 배포하지 않음

**원인**: Multi-cluster 설정 누락

**해결**:
```powershell
argocd cluster add portforge-dr-cluster --name dr-tokyo
```

---

## 참고 자료

- [AWS RDS Cross-Region Read Replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html#USER_ReadRepl.XRgn)
- [DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- [S3 Cross-Region Replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html)
- [ECR Replication](https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html)
- [Route 53 Failover Routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)

---

## 라이선스

MIT License

---

## 작성자

PortForge Team  
작성일: 2026-01-23
