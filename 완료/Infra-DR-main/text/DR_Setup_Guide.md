# DR 구성 가이드

Tokyo(ap-northeast-1) 리전에 DR 환경을 구축하기 위한 상세 가이드입니다.

## 목차

1. [전체 진행 순서](#전체-진행-순서)
2. [Phase 1: Seoul 사전 준비](#phase-1-seoul-사전-준비)
3. [Phase 2: Tokyo 리소스 생성 (수동)](#phase-2-tokyo-리소스-생성-수동)
4. [Phase 3: Tokyo 인프라 생성 (Terraform)](#phase-3-tokyo-인프라-생성-terraform)
5. [Phase 4: 모니터링/알림 설정](#phase-4-모니터링알림-설정)
6. [Phase 5: Route 53 Failover 설정](#phase-5-route-53-failover-설정)
7. [DR 전환 절차](#dr-전환-절차)

---

## 전체 진행 순서

### 개요

| Phase | 작업 | 예상 소요시간 |
|-------|------|---------------|
| Phase 1 | Seoul 사전 준비 | 30분 |
| Phase 2 | Tokyo 리소스 생성 (수동) | 2시간 |
| Phase 3 | Tokyo 인프라 생성 (Terraform) | 40분 |
| Phase 4 | 모니터링/알림 설정 | 40분 |
| Phase 5 | Route 53 Failover 설정 | 20분 |
| **총합** | | **약 4시간** |

### 리소스별 DR 전략 요약

| 리소스 | DR 방식 | 관리 | RPO |
|--------|---------|------|-----|
| VPC/EKS | Terraform | 자동 | - |
| RDS | Cross-Region Read Replica | 수동 | ~5초 |
| DynamoDB | Global Table | 수동 | ~1초 |
| S3 | CRR (Cross-Region Replication) | 수동 | ~15분 |
| ECR | Replication | 수동 | - |
| Cognito | Lambda 동기화 | 수동 | 실시간 |
| Secrets Manager | Cross-Region Replication | 수동 | - |

---

## Phase 1: Seoul 사전 준비

Seoul 리전에서 DR 복제를 위한 사전 설정을 진행합니다.

### 1.1 S3 Versioning 활성화

CRR(Cross-Region Replication)을 위해 Source 버킷에 Versioning이 필수입니다.

```powershell
# 각 버킷에 Versioning 활성화
aws s3api put-bucket-versioning `
  --bucket portforge-front `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-2

aws s3api put-bucket-versioning `
  --bucket portforge-team `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-2

aws s3api put-bucket-versioning `
  --bucket portforge-log `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-2
```

**확인:**
```powershell
aws s3api get-bucket-versioning --bucket portforge-front --region ap-northeast-2
# 출력: {"Status": "Enabled"}
```

### 1.2 RDS 백업 활성화

Read Replica 생성을 위해 자동 백업이 활성화되어 있어야 합니다.

```powershell
# 현재 백업 설정 확인
aws rds describe-db-instances `
  --db-instance-identifier portforge-test-rds `
  --region ap-northeast-2 `
  --query 'DBInstances[0].BackupRetentionPeriod'

# 0이면 백업 활성화 (7일 보관)
aws rds modify-db-instance `
  --db-instance-identifier portforge-test-rds `
  --backup-retention-period 7 `
  --apply-immediately `
  --region ap-northeast-2
```

**주의:** 백업 활성화 후 첫 스냅샷 생성까지 시간이 걸릴 수 있습니다.

### 1.3 DynamoDB Stream 활성화

Global Table 생성을 위해 DynamoDB Stream이 필수입니다.

```powershell
# team_chats_ddb 테이블
aws dynamodb update-table `
  --table-name team_chats_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2

# chat_rooms_ddb 테이블
aws dynamodb update-table `
  --table-name chat_rooms_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2
```

**확인 (1분 대기 후):**
```powershell
aws dynamodb describe-table `
  --table-name team_chats_ddb `
  --region ap-northeast-2 `
  --query 'Table.StreamSpecification'
# 출력: {"StreamEnabled": true, "StreamViewType": "NEW_AND_OLD_IMAGES"}
```

### 1.4 ECR Replication 설정

새로 Push되는 이미지를 Tokyo로 자동 복제합니다.

```powershell
aws ecr put-replication-configuration `
  --replication-configuration '{
    "rules": [{
      "destinations": [{
        "region": "ap-northeast-1",
        "registryId": "023490709500"
      }]
    }]
  }' `
  --region ap-northeast-2
```

**확인:**
```powershell
aws ecr describe-registry --region ap-northeast-2
```

### 1.5 Cognito Lambda Trigger 설정

회원가입 시 Tokyo Cognito에 사용자를 동기화하는 Lambda를 설정합니다.

#### 1.5.1 Lambda 함수 생성

**AWS Console > Lambda > Create function**

- Function name: `cognito-dr-sync`
- Runtime: Python 3.11
- Architecture: arm64

**코드:**
```python
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Seoul Cognito 회원가입 완료 시 Tokyo Cognito에 동일 사용자 생성
    """
    # 이벤트에서 사용자 정보 추출
    user_attributes = event['request']['userAttributes']
    email = user_attributes.get('email')
    nickname = user_attributes.get('nickname', '')
    email_verified = user_attributes.get('email_verified', 'false')
    
    logger.info(f"Syncing user to Tokyo: {email}")
    
    # Tokyo Cognito 클라이언트
    tokyo_cognito = boto3.client('cognito-idp', region_name='ap-northeast-1')
    tokyo_pool_id = os.environ['TOKYO_USER_POOL_ID']
    
    try:
        # Tokyo에 사용자 생성
        tokyo_cognito.admin_create_user(
            UserPoolId=tokyo_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': email_verified},
                {'Name': 'nickname', 'Value': nickname}
            ],
            MessageAction='SUPPRESS'  # 환영 이메일 발송 안함
        )
        logger.info(f"Successfully synced user to Tokyo: {email}")
        
    except tokyo_cognito.exceptions.UsernameExistsException:
        logger.info(f"User already exists in Tokyo: {email}")
    except Exception as e:
        logger.error(f"Failed to sync user to Tokyo: {email}, Error: {str(e)}")
        # 에러가 발생해도 Seoul 회원가입은 진행되어야 함
    
    # 반드시 event 반환 (Cognito Trigger 규칙)
    return event
```

#### 1.5.2 환경변수 설정

| Key | Value |
|-----|-------|
| TOKYO_USER_POOL_ID | ap-northeast-1_XXXXXXXX (Phase 2에서 생성 후 입력) |

#### 1.5.3 IAM Role 권한 추가

Lambda 실행 역할에 다음 정책 추가:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminGetUser"
            ],
            "Resource": "arn:aws:cognito-idp:ap-northeast-1:023490709500:userpool/*"
        }
    ]
}
```

#### 1.5.4 Cognito Trigger 연결

**AWS Console > Cognito > User Pool > User pool properties > Lambda triggers**

- Post confirmation: `cognito-dr-sync` 선택

---

## Phase 2: Tokyo 리소스 생성 (수동)

Terraform으로 관리하지 않는 리소스들을 수동으로 생성합니다.

### 2.1 S3 DR 버킷 생성 및 CRR 설정

#### 2.1.1 Tokyo 버킷 생성

```powershell
# DR 버킷 생성 (버킷명에 -dr suffix)
aws s3 mb s3://portforge-front-dr --region ap-northeast-1
aws s3 mb s3://portforge-team-dr --region ap-northeast-1
aws s3 mb s3://portforge-log-dr --region ap-northeast-1

# Versioning 활성화 (CRR 필수)
aws s3api put-bucket-versioning `
  --bucket portforge-front-dr `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-1

aws s3api put-bucket-versioning `
  --bucket portforge-team-dr `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-1

aws s3api put-bucket-versioning `
  --bucket portforge-log-dr `
  --versioning-configuration Status=Enabled `
  --region ap-northeast-1
```

#### 2.1.2 CRR IAM Role 생성

**AWS Console > IAM > Roles > Create role**

- Trusted entity: S3
- Role name: `s3-crr-role`

**정책:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetReplicationConfiguration",
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::portforge-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObjectVersionForReplication",
                "s3:GetObjectVersionAcl",
                "s3:GetObjectVersionTagging"
            ],
            "Resource": "arn:aws:s3:::portforge-*/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ReplicateObject",
                "s3:ReplicateDelete",
                "s3:ReplicateTags"
            ],
            "Resource": "arn:aws:s3:::portforge-*-dr/*"
        }
    ]
}
```

#### 2.1.3 CRR Rule 설정 (AWS Console)

**S3 Console > portforge-team > Management > Replication rules > Create replication rule**

| 설정 | 값 |
|------|-----|
| Rule name | dr-replication |
| Status | Enabled |
| Source bucket | This bucket (전체) |
| Destination | portforge-team-dr (ap-northeast-1) |
| IAM role | s3-crr-role |

나머지 버킷(portforge-front, portforge-log)도 동일하게 설정합니다.

#### 2.1.4 기존 데이터 수동 복제

CRR은 Rule 생성 이후의 새 객체만 복제합니다. 기존 데이터는 수동 복제가 필요합니다.

```powershell
# 기존 데이터 복제
aws s3 sync s3://portforge-front s3://portforge-front-dr --region ap-northeast-1
aws s3 sync s3://portforge-team s3://portforge-team-dr --region ap-northeast-1
aws s3 sync s3://portforge-log s3://portforge-log-dr --region ap-northeast-1
```

### 2.2 RDS Read Replica 생성

#### 2.2.1 Read Replica 생성

```powershell
aws rds create-db-instance-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --source-db-instance-identifier arn:aws:rds:ap-northeast-2:023490709500:db:portforge-test-rds `
  --db-instance-class db.t3.micro `
  --region ap-northeast-1 `
  --no-multi-az `
  --publicly-accessible false
```

#### 2.2.2 생성 완료 대기 (10~15분)

```powershell
# 상태 확인
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].DBInstanceStatus'

# "available"이 될 때까지 대기
```

#### 2.2.3 Replica Lag 확인

```powershell
aws cloudwatch get-metric-statistics `
  --namespace AWS/RDS `
  --metric-name ReplicaLag `
  --dimensions Name=DBInstanceIdentifier,Value=portforge-dr-rds-replica `
  --start-time (Get-Date).AddMinutes(-10).ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --end-time (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ") `
  --period 60 `
  --statistics Average `
  --region ap-northeast-1
```

**정상:** ReplicaLag < 5초

#### 2.2.4 Endpoint 확인

```powershell
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].Endpoint.Address'

# 출력 예: portforge-dr-rds-replica.xxxxx.ap-northeast-1.rds.amazonaws.com
```

이 Endpoint를 Tokyo ConfigMap의 `DATABASE_HOST`에 사용합니다.

### 2.3 DynamoDB Global Table 설정

#### 2.3.1 Global Table 생성

```powershell
# team_chats_ddb
aws dynamodb create-global-table `
  --global-table-name team_chats_ddb `
  --replication-group RegionName=ap-northeast-2 RegionName=ap-northeast-1 `
  --region ap-northeast-2

# chat_rooms_ddb
aws dynamodb create-global-table `
  --global-table-name chat_rooms_ddb `
  --replication-group RegionName=ap-northeast-2 RegionName=ap-northeast-1 `
  --region ap-northeast-2
```

#### 2.3.2 생성 완료 대기 (5~10분)

```powershell
aws dynamodb describe-global-table `
  --global-table-name team_chats_ddb `
  --region ap-northeast-2

# ReplicationGroup의 각 리전 상태가 "ACTIVE"인지 확인
```

#### 2.3.3 Tokyo에서 테이블 확인

```powershell
aws dynamodb describe-table `
  --table-name team_chats_ddb `
  --region ap-northeast-1

aws dynamodb describe-table `
  --table-name chat_rooms_ddb `
  --region ap-northeast-1
```

### 2.4 ECR 기존 이미지 수동 복제

ECR Replication은 설정 이후의 새 이미지만 복제합니다. 기존 이미지는 수동 복제가 필요합니다.

#### 2.4.1 Tokyo에 Repository 생성

```powershell
$repos = @("auth-service", "team-service", "project-service", "ai-service", "support-service", "infra-bot", "slack-monitoring-bot")

foreach ($repo in $repos) {
    aws ecr create-repository --repository-name $repo --region ap-northeast-1
}
```

#### 2.4.2 이미지 복제

```powershell
$accountId = "023490709500"

# ECR 로그인 (양쪽 리전)
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $accountId.dkr.ecr.ap-northeast-2.amazonaws.com
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin $accountId.dkr.ecr.ap-northeast-1.amazonaws.com

# 각 서비스 이미지 복제
foreach ($repo in $repos) {
    Write-Host "Copying $repo..."
    docker pull $accountId.dkr.ecr.ap-northeast-2.amazonaws.com/${repo}:latest
    docker tag $accountId.dkr.ecr.ap-northeast-2.amazonaws.com/${repo}:latest $accountId.dkr.ecr.ap-northeast-1.amazonaws.com/${repo}:latest
    docker push $accountId.dkr.ecr.ap-northeast-1.amazonaws.com/${repo}:latest
}
```

### 2.5 Cognito User Pool 생성

#### 2.5.1 User Pool 생성 (AWS Console)

**AWS Console > Cognito > Create user pool**

| 설정 | 값 |
|------|-----|
| Pool name | portforge-dr-user-pool |
| Sign-in options | Email |
| Password policy | Seoul과 동일 (최소 8자, 대소문자, 숫자, 특수문자) |
| MFA | Off |
| Self-registration | Enabled |
| Email | Cognito default |

#### 2.5.2 App Client 생성

**User pool > App integration > Create app client**

| 설정 | 값 |
|------|-----|
| App client name | portforge-dr-client |
| Client secret | Generate a client secret |
| Authentication flows | ALLOW_USER_PASSWORD_AUTH, ALLOW_REFRESH_TOKEN_AUTH |

#### 2.5.3 OAuth 2.0 설정

**App client > Hosted UI**

| 설정 | 값 |
|------|-----|
| Callback URLs | https://portforge.org/auth/callback |
| Sign-out URLs | https://portforge.org |
| OAuth 2.0 grant types | Authorization code grant |
| OpenID Connect scopes | openid, email, profile |

#### 2.5.4 Google Identity Provider 추가

**User pool > Sign-in experience > Federated identity provider sign-in > Add identity provider > Google**

| 설정 | 값 |
|------|-----|
| Client ID | Seoul과 동일한 Google Client ID |
| Client secret | Seoul과 동일한 Google Client Secret |
| Authorized scopes | openid email profile |

**주의:** Google Cloud Console에서 Redirect URI 추가 불필요 (도메인 동일)

#### 2.5.5 User Pool ID 및 Client ID 기록

생성 완료 후 다음 값을 기록합니다:

| 항목 | 예시 값 |
|------|---------|
| User Pool ID | ap-northeast-1_XXXXXXXX |
| App Client ID | xxxxxxxxxxxxxxxxxxxxxxxxxx |
| Cognito Domain | portforge-dr (설정 필요) |

이 값들을 Phase 1의 Lambda 환경변수와 Tokyo ConfigMap에 사용합니다.

### 2.6 Secrets Manager 복제

#### 2.6.1 AWS Console에서 복제

**AWS Console > Secrets Manager > 시크릿 선택 > Actions > Replicate secret to other regions**

복제할 시크릿:
- `portforge/ai-service/rds`
- `portforge/slack-bot/tokens`
- `portforge/aws/bedrock-credentials`

| 설정 | 값 |
|------|-----|
| Region | ap-northeast-1 |
| Encryption key | aws/secretsmanager (기본값) |

#### 2.6.2 복제 확인

```powershell
aws secretsmanager list-secrets --region ap-northeast-1
```

### 2.7 ACM 인증서 발급

#### 2.7.1 인증서 요청

```powershell
aws acm request-certificate `
  --domain-name "*.portforge.org" `
  --subject-alternative-names "portforge.org" `
  --validation-method DNS `
  --region ap-northeast-1
```

#### 2.7.2 DNS 검증

```powershell
# 인증서 ARN 확인
aws acm list-certificates --region ap-northeast-1

# CNAME 레코드 확인
aws acm describe-certificate `
  --certificate-arn arn:aws:acm:ap-northeast-1:023490709500:certificate/xxxxx `
  --region ap-northeast-1 `
  --query 'Certificate.DomainValidationOptions'
```

**Route 53에 CNAME 레코드 추가:**

| Name | Type | Value |
|------|------|-------|
| _xxxxx.portforge.org | CNAME | _xxxxx.acm-validations.aws |

#### 2.7.3 검증 완료 대기 (최대 30분)

```powershell
aws acm describe-certificate `
  --certificate-arn arn:aws:acm:ap-northeast-1:023490709500:certificate/xxxxx `
  --region ap-northeast-1 `
  --query 'Certificate.Status'

# "ISSUED"가 될 때까지 대기
```

---

## Phase 3: Tokyo 인프라 생성 (Terraform)

VPC, EKS, IAM 등 핵심 인프라를 Terraform으로 생성합니다.

### 3.1 사전 준비

#### 3.1.1 AWS CLI 프로필 확인

```powershell
aws sts get-caller-identity
```

#### 3.1.2 Terraform 버전 확인

```powershell
terraform version
# 1.0.0 이상 필요
```

### 3.2 Terraform 실행

```powershell
cd Infra-DR

# 초기화
terraform init

# 실행 계획 확인
terraform plan

# 적용 (약 20분 소요)
terraform apply
```

**생성되는 리소스:**
- VPC (3 Public Subnets, 3 Private Subnets)
- EKS Cluster + Node Group
- IAM Roles (EKS, External Secrets, CloudWatch)
- Route 53 Health Check
- CloudWatch Alarms

### 3.3 kubeconfig 업데이트

```powershell
aws eks update-kubeconfig `
  --name portforge-dr-cluster `
  --region ap-northeast-1
```

### 3.4 클러스터 연결 확인

```powershell
kubectl get nodes
kubectl get ns
```

### 3.5 Helm 배포

Terraform에서 Helm provider로 자동 배포되지만, 수동 확인이 필요한 경우:

```powershell
# ArgoCD 확인
kubectl get pods -n argocd

# External Secrets Operator 확인
kubectl get pods -n external-secrets

# AWS Load Balancer Controller 확인
kubectl get pods -n kube-system | Select-String "aws-load-balancer"
```

---

## Phase 4: 모니터링/알림 설정

Tokyo DR 환경은 AWS 네이티브 모니터링(CloudWatch)을 사용합니다.

### 4.1 Container Insights 활성화

#### 4.1.1 EKS Addon 설치

```powershell
aws eks create-addon `
  --cluster-name portforge-dr-cluster `
  --addon-name amazon-cloudwatch-observability `
  --region ap-northeast-1
```

#### 4.1.2 설치 확인

```powershell
aws eks describe-addon `
  --cluster-name portforge-dr-cluster `
  --addon-name amazon-cloudwatch-observability `
  --region ap-northeast-1 `
  --query 'addon.status'

# "ACTIVE"가 될 때까지 대기
```

#### 4.1.3 CloudWatch Agent 확인

```powershell
kubectl get pods -n amazon-cloudwatch
```

### 4.2 CloudWatch Dashboard 생성

#### 4.2.1 AWS Console에서 생성

**CloudWatch Console > Dashboards > Create dashboard**

Dashboard name: `portforge-dr-dashboard`

#### 4.2.2 위젯 추가

**EKS 모니터링:**
| 위젯 | 메트릭 |
|------|--------|
| Node CPU | ContainerInsights > ClusterName > node_cpu_utilization |
| Node Memory | ContainerInsights > ClusterName > node_memory_utilization |
| Pod Count | ContainerInsights > ClusterName > pod_number_of_running_pods |

**RDS 모니터링:**
| 위젯 | 메트릭 |
|------|--------|
| CPU Utilization | RDS > DBInstanceIdentifier > CPUUtilization |
| Database Connections | RDS > DBInstanceIdentifier > DatabaseConnections |
| Replica Lag | RDS > DBInstanceIdentifier > ReplicaLag |

**DynamoDB 모니터링:**
| 위젯 | 메트릭 |
|------|--------|
| Read Capacity | DynamoDB > TableName > ConsumedReadCapacityUnits |
| Write Capacity | DynamoDB > TableName > ConsumedWriteCapacityUnits |

**ALB 모니터링:**
| 위젯 | 메트릭 |
|------|--------|
| Request Count | ApplicationELB > LoadBalancer > RequestCount |
| Target Response Time | ApplicationELB > LoadBalancer > TargetResponseTime |
| HTTP 5xx Count | ApplicationELB > LoadBalancer > HTTPCode_Target_5XX_Count |

### 4.3 CloudWatch Alarms 생성

Terraform에서 기본 Alarm이 생성되지만, 추가 Alarm이 필요한 경우:

#### 4.3.1 RDS Replica Lag Alarm

```powershell
aws cloudwatch put-metric-alarm `
  --alarm-name "DR-RDS-ReplicaLag-High" `
  --alarm-description "RDS Replica Lag exceeds 60 seconds" `
  --metric-name ReplicaLag `
  --namespace AWS/RDS `
  --statistic Average `
  --period 300 `
  --threshold 60 `
  --comparison-operator GreaterThanThreshold `
  --dimensions Name=DBInstanceIdentifier,Value=portforge-dr-rds-replica `
  --evaluation-periods 2 `
  --alarm-actions arn:aws:sns:ap-northeast-1:023490709500:dr-alerts `
  --region ap-northeast-1
```

#### 4.3.2 EKS Node CPU Alarm

```powershell
aws cloudwatch put-metric-alarm `
  --alarm-name "DR-EKS-NodeCPU-High" `
  --alarm-description "EKS Node CPU exceeds 80%" `
  --metric-name node_cpu_utilization `
  --namespace ContainerInsights `
  --statistic Average `
  --period 300 `
  --threshold 80 `
  --comparison-operator GreaterThanThreshold `
  --dimensions Name=ClusterName,Value=portforge-dr-cluster `
  --evaluation-periods 2 `
  --alarm-actions arn:aws:sns:ap-northeast-1:023490709500:dr-alerts `
  --region ap-northeast-1
```

### 4.4 Slack 알림 Lambda 생성

#### 4.4.1 SNS Topic 생성

```powershell
aws sns create-topic --name dr-alerts --region ap-northeast-1
```

#### 4.4.2 Lambda 함수 생성

**AWS Console > Lambda > Create function**

| 설정 | 값 |
|------|-----|
| Function name | dr-slack-notification |
| Runtime | Python 3.11 |
| Architecture | arm64 |

**코드:**
```python
import json
import urllib.request
import os

def lambda_handler(event, context):
    webhook_url = os.environ['SLACK_WEBHOOK_URL']
    
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        
        alarm_name = message.get('AlarmName', 'Unknown')
        state = message.get('NewStateValue', 'Unknown')
        reason = message.get('NewStateReason', '')
        timestamp = message.get('StateChangeTime', '')
        
        # 상태별 이모지
        emoji = "🔴" if state == "ALARM" else "✅" if state == "OK" else "⚠️"
        
        slack_message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} [DR] {alarm_name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*상태:* {state}"},
                        {"type": "mrkdwn", "text": f"*시간:* {timestamp}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*원인:* {reason[:200]}..."
                    }
                }
            ]
        }
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(slack_message).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req)
    
    return {'statusCode': 200}
```

#### 4.4.3 환경변수 설정

| Key | Value |
|-----|-------|
| SLACK_WEBHOOK_URL | https://hooks.slack.com/services/xxx/xxx/xxx |

#### 4.4.4 SNS 구독 추가

```powershell
# Lambda ARN 확인
$lambdaArn = aws lambda get-function `
  --function-name dr-slack-notification `
  --region ap-northeast-1 `
  --query 'Configuration.FunctionArn' `
  --output text

# SNS 구독
aws sns subscribe `
  --topic-arn arn:aws:sns:ap-northeast-1:023490709500:dr-alerts `
  --protocol lambda `
  --notification-endpoint $lambdaArn `
  --region ap-northeast-1
```

#### 4.4.5 Lambda 권한 추가

```powershell
aws lambda add-permission `
  --function-name dr-slack-notification `
  --statement-id sns-trigger `
  --action lambda:InvokeFunction `
  --principal sns.amazonaws.com `
  --source-arn arn:aws:sns:ap-northeast-1:023490709500:dr-alerts `
  --region ap-northeast-1
```

---

## Phase 5: Route 53 Failover 설정

Seoul 장애 시 자동으로 Tokyo로 트래픽을 전환합니다.

### 5.1 Health Check 생성

Terraform에서 생성되지만, 수동 확인/생성이 필요한 경우:

```powershell
aws route53 create-health-check `
  --caller-reference "seoul-alb-health-$(Get-Date -Format 'yyyyMMddHHmmss')" `
  --health-check-config '{
    "Type": "HTTPS",
    "FullyQualifiedDomainName": "api.portforge.org",
    "Port": 443,
    "ResourcePath": "/health",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }'
```

### 5.2 Failover 레코드 설정

#### 5.2.1 Primary 레코드 (Seoul)

**Route 53 Console > Hosted zone > Create record**

| 설정 | 값 |
|------|-----|
| Record name | api.portforge.org |
| Record type | A |
| Alias | Yes |
| Route traffic to | Seoul ALB |
| Routing policy | Failover |
| Failover record type | Primary |
| Health check | seoul-alb-health |
| Record ID | seoul-primary |

#### 5.2.2 Secondary 레코드 (Tokyo)

| 설정 | 값 |
|------|-----|
| Record name | api.portforge.org |
| Record type | A |
| Alias | Yes |
| Route traffic to | Tokyo ALB |
| Routing policy | Failover |
| Failover record type | Secondary |
| Health check | (없음) |
| Record ID | tokyo-secondary |

### 5.3 Failover 테스트

#### 5.3.1 현재 상태 확인

```powershell
# DNS 조회
nslookup api.portforge.org

# Health Check 상태
aws route53 get-health-check-status `
  --health-check-id xxxxx
```

#### 5.3.2 Failover 시뮬레이션

**주의:** 실제 서비스에 영향을 줄 수 있으므로 테스트 환경에서만 수행

1. Seoul ALB의 Target Group에서 모든 타겟을 Unhealthy로 변경
2. Health Check가 Unhealthy로 변경되는지 확인 (약 90초)
3. DNS가 Tokyo ALB로 변경되는지 확인
4. 테스트 완료 후 원복

---

## DR 전환 절차

실제 DR 상황 발생 시 수행할 절차입니다.

### 자동 전환 (Route 53 Failover)

Seoul ALB Health Check 실패 시 자동으로 Tokyo로 트래픽 전환됩니다.

**자동 전환 조건:**
- Health Check 3회 연속 실패 (약 90초)
- DNS TTL 만료 후 Tokyo로 라우팅

### 수동 전환 절차

자동 전환이 되지 않거나, 수동으로 DR을 선언해야 하는 경우:

#### Step 1: DR 선언

- 담당자가 DR 상황임을 판단
- Slack/이메일로 팀에 공지

#### Step 2: RDS Promote

```powershell
aws rds promote-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1
```

**주의:** Promote 후에는 Seoul RDS와의 복제가 끊어집니다.

#### Step 3: Route 53 수동 전환 (필요시)

```powershell
# Primary 레코드 비활성화
aws route53 change-resource-record-sets `
  --hosted-zone-id ZXXXXX `
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.portforge.org",
        "Type": "A",
        "SetIdentifier": "seoul-primary",
        "Failover": "PRIMARY",
        "AliasTarget": {
          "HostedZoneId": "ZXXXXX",
          "DNSName": "seoul-alb.ap-northeast-2.elb.amazonaws.com",
          "EvaluateTargetHealth": false
        },
        "HealthCheckId": "xxxxx"
      }
    }]
  }'
```

#### Step 4: Tokyo ConfigMap 확인

Tokyo 환경의 ConfigMap이 올바른 값으로 설정되어 있는지 확인:

```yaml
# 확인할 값들
AWS_REGION: "ap-northeast-1"
COGNITO_REGION: "ap-northeast-1"
COGNITO_USER_POOL_ID: "ap-northeast-1_XXXXXXXX"
COGNITO_APP_CLIENT_ID: "tokyo-client-id"
DATABASE_HOST: "portforge-dr-rds-replica.xxxxx.ap-northeast-1.rds.amazonaws.com"
S3_BUCKET: "portforge-team-dr"
```

#### Step 5: 서비스 상태 확인

```powershell
# Pod 상태 확인
kubectl get pods -A

# 서비스 엔드포인트 테스트
curl https://api.portforge.org/health
```

#### Step 6: 사용자 공지

- 서비스 복구 완료 공지
- 일반 로그인 사용자: 비밀번호 재설정 안내
- 소셜 로그인 사용자: 즉시 이용 가능

---

## 체크리스트

### Phase 1 완료 체크리스트
- [ ] S3 Versioning 활성화
- [ ] RDS 백업 활성화
- [ ] DynamoDB Stream 활성화
- [ ] ECR Replication 설정
- [ ] Cognito Lambda Trigger 설정

### Phase 2 완료 체크리스트
- [ ] S3 DR 버킷 생성
- [ ] S3 CRR 설정
- [ ] 기존 S3 데이터 복제
- [ ] RDS Read Replica 생성
- [ ] DynamoDB Global Table 설정
- [ ] ECR Repository 생성
- [ ] 기존 ECR 이미지 복제
- [ ] Cognito User Pool 생성
- [ ] Cognito App Client 생성
- [ ] Cognito Google OAuth 설정
- [ ] Secrets Manager 복제
- [ ] ACM 인증서 발급

### Phase 3 완료 체크리스트
- [ ] terraform init
- [ ] terraform plan
- [ ] terraform apply
- [ ] kubeconfig 업데이트
- [ ] kubectl 연결 확인

### Phase 4 완료 체크리스트
- [ ] Container Insights 활성화
- [ ] CloudWatch Dashboard 생성
- [ ] CloudWatch Alarms 생성
- [ ] SNS Topic 생성
- [ ] Slack 알림 Lambda 생성
- [ ] SNS-Lambda 연결

### Phase 5 완료 체크리스트
- [ ] Health Check 생성
- [ ] Primary 레코드 설정
- [ ] Secondary 레코드 설정
- [ ] Failover 테스트

---

## 주의사항

1. **S3 버킷명**: 글로벌 유니크, 삭제 후 24시간 동일 이름 재생성 불가
2. **RDS Promote**: 한 번 Promote하면 다시 Replica로 변경 불가 (새로 생성 필요)
3. **DynamoDB Global Table**: 삭제 시 양쪽 리전 데이터 모두 삭제됨
4. **Cognito**: 비밀번호 동기화 불가, DR 전환 시 비밀번호 재설정 필요
5. **Secrets Manager**: 삭제 시 7~30일 복구 기간 존재
6. **ECR Replication**: 새 이미지만 자동 복제, 기존 이미지는 수동 복제 필요
