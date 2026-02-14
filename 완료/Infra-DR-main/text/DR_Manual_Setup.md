# DR 수동 설정 가이드

Terraform으로 관리하지 않는 리소스들의 수동 설정 가이드입니다.

## 수동 설정이 필요한 이유

| 리소스 | 이유 |
|--------|------|
| S3 | 버킷명 글로벌 유니크, 삭제 후 24시간 대기 |
| RDS Read Replica | Primary 의존성, Promote 작업 필요 |
| DynamoDB Global Table | 기존 테이블 변환 작업 |
| ECR Replication | Registry 레벨 설정, 기존 이미지 수동 복제 |
| Cognito | 사용자 데이터 보존, 삭제 시 복구 불가 |
| Secrets Manager | 삭제 대기 기간 7~30일 |
| ACM 인증서 | 도메인 검증 필요 |
| Lambda (Slack) | 코드 수정/테스트 빈번 |
| CloudWatch Dashboard | UI 구성이 더 직관적 |
| Container Insights | EKS Addon으로 관리가 안정적 |

---

## 1. S3 버킷 생성 및 CRR 설정

### 1.1 DR 버킷 생성

```powershell
# 버킷 생성
aws s3 mb s3://portforge-front-dr --region ap-northeast-1
aws s3 mb s3://portforge-team-dr --region ap-northeast-1
aws s3 mb s3://portforge-log-dr --region ap-northeast-1

# Versioning 활성화 (CRR 필수)
aws s3api put-bucket-versioning --bucket portforge-front-dr --versioning-configuration Status=Enabled --region ap-northeast-1
aws s3api put-bucket-versioning --bucket portforge-team-dr --versioning-configuration Status=Enabled --region ap-northeast-1
aws s3api put-bucket-versioning --bucket portforge-log-dr --versioning-configuration Status=Enabled --region ap-northeast-1
```

### 1.2 Primary 버킷 Versioning 활성화

```powershell
aws s3api put-bucket-versioning --bucket portforge-front --versioning-configuration Status=Enabled --region ap-northeast-2
aws s3api put-bucket-versioning --bucket portforge-team --versioning-configuration Status=Enabled --region ap-northeast-2
aws s3api put-bucket-versioning --bucket portforge-log --versioning-configuration Status=Enabled --region ap-northeast-2
```

### 1.3 CRR 설정 (AWS Console)

1. S3 Console > portforge-team > Management > Replication rules
2. Create replication rule
   - Rule name: `dr-replication`
   - Status: Enabled
   - Source: This bucket
   - Destination: `portforge-team-dr` (ap-northeast-1)
   - IAM role: Create new role
3. 나머지 버킷도 동일하게 설정

---

## 2. RDS Read Replica 생성

### 2.1 Primary RDS 백업 활성화 확인

```powershell
aws rds describe-db-instances --db-instance-identifier portforge-test-rds --region ap-northeast-2 --query 'DBInstances[0].BackupRetentionPeriod'

# 0이면 백업 활성화
aws rds modify-db-instance --db-instance-identifier portforge-test-rds --backup-retention-period 7 --region ap-northeast-2
```

### 2.2 Read Replica 생성

```powershell
aws rds create-db-instance-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --source-db-instance-identifier arn:aws:rds:ap-northeast-2:023490709500:db:portforge-test-rds `
  --db-instance-class db.t3.micro `
  --region ap-northeast-1 `
  --no-multi-az `
  --publicly-accessible false
```

### 2.3 생성 확인 (10~15분 소요)

```powershell
aws rds describe-db-instances --db-instance-identifier portforge-dr-rds-replica --region ap-northeast-1 --query 'DBInstances[0].DBInstanceStatus'
```

### 2.4 DR 전환 시 Promote

```powershell
aws rds promote-read-replica --db-instance-identifier portforge-dr-rds-replica --region ap-northeast-1
```

---

## 3. DynamoDB Global Table 설정

### 3.1 Stream 활성화

```powershell
aws dynamodb update-table `
  --table-name team_chats_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2

aws dynamodb update-table `
  --table-name chat_rooms_ddb `
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES `
  --region ap-northeast-2
```

### 3.2 Stream 활성화 확인 (1분 대기)

```powershell
aws dynamodb describe-table --table-name team_chats_ddb --region ap-northeast-2 --query 'Table.StreamSpecification'
```

### 3.3 Global Table 생성

```powershell
aws dynamodb create-global-table `
  --global-table-name team_chats_ddb `
  --replication-group RegionName=ap-northeast-2 RegionName=ap-northeast-1 `
  --region ap-northeast-2

aws dynamodb create-global-table `
  --global-table-name chat_rooms_ddb `
  --replication-group RegionName=ap-northeast-2 RegionName=ap-northeast-1 `
  --region ap-northeast-2
```

### 3.4 Global Table 상태 확인 (5~10분 소요)

```powershell
aws dynamodb describe-global-table --global-table-name team_chats_ddb --region ap-northeast-2
```

### 3.5 Tokyo에서 테이블 확인

```powershell
aws dynamodb describe-table --table-name team_chats_ddb --region ap-northeast-1
```

---

## 4. ECR Replication 설정

### 4.1 Replication 설정 (Seoul에서)

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

### 4.2 기존 이미지 수동 복제

```powershell
$repos = @("auth-service", "team-service", "project-service", "ai-service", "support-service", "infra-bot", "slack-monitoring-bot")
$accountId = "023490709500"

# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $accountId.dkr.ecr.ap-northeast-2.amazonaws.com
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin $accountId.dkr.ecr.ap-northeast-1.amazonaws.com

foreach ($repo in $repos) {
    docker pull $accountId.dkr.ecr.ap-northeast-2.amazonaws.com/${repo}:latest
    docker tag $accountId.dkr.ecr.ap-northeast-2.amazonaws.com/${repo}:latest $accountId.dkr.ecr.ap-northeast-1.amazonaws.com/${repo}:latest
    docker push $accountId.dkr.ecr.ap-northeast-1.amazonaws.com/${repo}:latest
}
```

---

## 5. Cognito User Pool 설정

### 5.1 Cognito DR 한계점

AWS Cognito는 Cross-Region Replication을 지원하지 않아 다음 제약이 있습니다:

| 제약사항 | 설명 |
|----------|------|
| 토큰 호환 불가 | Seoul에서 발급한 토큰은 Tokyo에서 검증 불가 (issuer 불일치) |
| 비밀번호 동기화 불가 | Cognito는 비밀번호 해시를 외부에 노출하지 않음 |
| User Pool ID 상이 | 각 리전별로 별도의 User Pool ID 발급 |

**토큰 검증 로직** (Auth 서비스):
```python
# issuer가 리전별로 다르기 때문에 Seoul 토큰은 Tokyo에서 검증 실패
issuer=f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USERPOOL_ID}"
```

### 5.2 프로덕션 환경 대안

| 방식 | 설명 |
|------|------|
| Auth0, Okta | 기본적으로 Multi-Region 지원, 자동 Failover |
| 자체 JWT 서버 | 비밀번호 해시를 RDS에 저장, Read Replica로 복제 가능 |
| Firebase Auth | Google 글로벌 인프라 활용 |

### 5.3 현재 프로젝트 DR 전략

DR 전환 시 사용자 재로그인이 필요합니다:
- 일반 로그인 사용자: 비밀번호 재설정 또는 재로그인
- 소셜 로그인 사용자: 즉시 로그인 가능 (Google OAuth는 글로벌)
- RTO 영향: 약 30초 (재로그인 시간)

### 5.4 Tokyo User Pool 생성 (AWS Console)

1. Cognito Console > Create user pool
2. 설정값 (Seoul과 동일하게):
   - Pool name: `portforge-dr-user-pool`
   - Sign-in options: Email
   - Password policy: Seoul과 동일
   - MFA: Off
   - Self-registration: Enabled

### 5.5 App Client 생성

1. App integration > Create app client
2. 설정:
   - App client name: `portforge-dr-client`
   - Client secret: Generate
   - OAuth 2.0: Authorization code grant
   - Callback URLs: `https://portforge.org/callback`

### 5.6 Google OAuth 설정

1. Identity providers > Add Google
2. Seoul과 동일한 Google Client ID/Secret 사용
3. Google Cloud Console에서 Redirect URI 추가 필요 없음 (도메인 동일)

### 5.7 DR 전환 시 ConfigMap 변경

```yaml
# k8s/Auth/configmap.yaml (Tokyo용으로 변경)
data:
  COGNITO_REGION: "ap-northeast-1"
  COGNITO_USER_POOL_ID: "ap-northeast-1_XXXXXXXX"  # Tokyo User Pool ID
  COGNITO_APP_CLIENT_ID: "tokyo-app-client-id"
  AWS_REGION: "ap-northeast-1"
```

### 5.8 사용자 동기화 Lambda (선택)

Seoul Cognito의 Post Confirmation Trigger에 Lambda를 추가하여 Tokyo에 사용자를 미리 생성할 수 있습니다.
단, 비밀번호는 동기화되지 않으므로 DR 전환 시 비밀번호 재설정이 필요합니다.

```python
import boto3
import os

def lambda_handler(event, context):
    email = event['request']['userAttributes'].get('email')
    nickname = event['request']['userAttributes'].get('nickname', '')
    
    tokyo_cognito = boto3.client('cognito-idp', region_name='ap-northeast-1')
    
    try:
        tokyo_cognito.admin_create_user(
            UserPoolId=os.environ['TOKYO_USER_POOL_ID'],
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'nickname', 'Value': nickname}
            ],
            MessageAction='SUPPRESS'
        )
    except tokyo_cognito.exceptions.UsernameExistsException:
        pass
    
    return event
```

---

## 6. Secrets Manager 복제

### 6.1 AWS Console에서 복제

1. Secrets Manager Console > 시크릿 선택
2. Actions > Replicate secret to other regions
3. Region: ap-northeast-1 선택
4. 복제할 시크릿:
   - `portforge/ai-service/rds`
   - `portforge/slack-bot/tokens`
   - `portforge/aws/bedrock-credentials`

---

## 7. ACM 인증서 발급

### 7.1 Tokyo에서 인증서 요청

```powershell
aws acm request-certificate `
  --domain-name "*.portforge.org" `
  --validation-method DNS `
  --region ap-northeast-1
```

### 7.2 DNS 검증

1. ACM Console에서 CNAME 레코드 확인
2. Route 53에 CNAME 레코드 추가
3. 검증 완료 대기 (최대 30분)

---

## 8. CloudWatch 모니터링 설정

### 8.1 Container Insights 활성화

```powershell
# EKS Addon으로 설치
aws eks create-addon `
  --cluster-name portforge-dr-cluster `
  --addon-name amazon-cloudwatch-observability `
  --region ap-northeast-1
```

### 8.2 CloudWatch Agent 설치 (Helm)

```powershell
helm repo add aws-observability https://aws-observability.github.io/helm-charts
helm repo update

helm install amazon-cloudwatch-observability aws-observability/amazon-cloudwatch-observability `
  --namespace amazon-cloudwatch --create-namespace `
  --set clusterName=portforge-dr-cluster `
  --set region=ap-northeast-1
```

### 8.3 CloudWatch Dashboard 생성 (AWS Console)

1. CloudWatch Console > Dashboards > Create dashboard
2. 위젯 추가:
   - EKS Node CPU/Memory
   - RDS CPU/Connections/Replica Lag
   - DynamoDB Read/Write Capacity
   - ALB Request Count/Latency

### 8.4 Slack 알림 Lambda 생성

1. Lambda Console > Create function
2. Runtime: Python 3.11
3. 코드:

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
        description = message.get('AlarmDescription', '')
        
        emoji = "🔴" if state == "ALARM" else "✅"
        
        slack_message = {
            "text": f"{emoji} *{alarm_name}*\n상태: {state}\n{description}"
        }
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(slack_message).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req)
    
    return {'statusCode': 200}
```

4. 환경변수: `SLACK_WEBHOOK_URL` 설정
5. SNS Topic 구독 추가

---

## 9. CloudFront Origin Failover (선택)

### 9.1 AWS Console에서 설정

1. CloudFront Console > Distribution 선택
2. Origins > Create origin
   - Origin domain: `portforge-front-dr.s3.ap-northeast-1.amazonaws.com`
3. Origin groups > Create origin group
   - Primary: Seoul S3
   - Secondary: Tokyo S3
   - Failover criteria: 5xx errors

---

## 설정 완료 체크리스트

- [ ] S3 버킷 생성 및 CRR 설정
- [ ] RDS Read Replica 생성
- [ ] DynamoDB Global Table 설정
- [ ] ECR Replication 설정
- [ ] 기존 ECR 이미지 복제
- [ ] Cognito User Pool 생성
- [ ] Secrets Manager 복제
- [ ] ACM 인증서 발급
- [ ] Container Insights 활성화
- [ ] CloudWatch Dashboard 생성
- [ ] Slack 알림 Lambda 생성
- [ ] CloudFront Origin Failover (선택)

---

## 주의사항

1. S3 버킷 삭제 시 24시간 동일 이름 재생성 불가
2. RDS Read Replica Promote 후 다시 Replica로 변경 불가 (새로 생성 필요)
3. DynamoDB Global Table 삭제 시 양쪽 리전 데이터 모두 삭제됨
4. Secrets Manager 삭제 시 7~30일 복구 기간 존재
5. ECR Replication은 새 이미지만 자동 복제 (기존 이미지 수동)
