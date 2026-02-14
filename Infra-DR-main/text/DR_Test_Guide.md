# DR 테스트 가이드

## 1. 테스트 개요

| 항목 | 내용 |
|------|------|
| 목적 | DR 인프라가 정상 작동하는지 검증 |
| 주기 | 분기 1회 (권장) |
| 소요 시간 | 2~4시간 |
| 참여자 | DevOps, Backend 개발자 |

---

## 2. 테스트 유형

| 유형 | 설명 | 위험도 | 주기 |
|------|------|--------|------|
| 컴포넌트 테스트 | 개별 서비스 정상 동작 확인 | 🟢 낮음 | 월 1회 |
| Failover 시뮬레이션 | 실제 DR 전환 테스트 | 🟡 중간 | 분기 1회 |
| Failback 테스트 | Seoul 복귀 절차 검증 | 🟡 중간 | 분기 1회 |
| 전체 DR 훈련 | 실제 장애 상황 시뮬레이션 | 🔴 높음 | 연 1회 |

---

## 3. 사전 준비

### 3.1 테스트 환경 확인
```powershell
# Tokyo EKS 클러스터 연결
aws eks update-kubeconfig --region ap-northeast-1 --name portforge-dr-cluster

# 노드 상태 확인
kubectl get nodes

# Pod 상태 확인
kubectl get pods -A
```

### 3.2 모니터링 준비
- Grafana 대시보드 열기
- CloudWatch 콘솔 열기
- Slack 알림 채널 확인

### 3.3 롤백 계획 준비
- Seoul 클러스터 접속 정보 확인
- RDS 원본 엔드포인트 기록
- DNS 원복 명령어 준비

---

## 4. 컴포넌트 테스트 (월 1회)

### 4.1 EKS 클러스터 테스트

```powershell
# 1. 클러스터 상태 확인
aws eks describe-cluster --name portforge-dr-cluster --region ap-northeast-1 --query 'cluster.status'

# 2. 노드 상태 확인
kubectl get nodes -o wide

# 3. 시스템 Pod 상태 확인
kubectl get pods -n kube-system

# 4. 테스트 Pod 배포
kubectl run test-pod --image=nginx --restart=Never
kubectl get pod test-pod
kubectl delete pod test-pod
```

**예상 결과:**
- 클러스터 상태: `ACTIVE`
- 노드 2개: `Ready`
- 시스템 Pod: 모두 `Running`

### 4.2 RDS Read Replica 테스트

```powershell
# 1. Read Replica 상태 확인
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].DBInstanceStatus'

# 2. 복제 지연 확인
aws rds describe-db-instances `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1 `
  --query 'DBInstances[0].StatusInfos'

# 3. 연결 테스트 (EKS Pod에서)
kubectl run mysql-test --image=mysql:8 --restart=Never --rm -it -- `
  mysql -h <DR_RDS_ENDPOINT> -u <USERNAME> -p -e "SELECT 1;"
```

**예상 결과:**
- 상태: `available`
- 복제 지연: 1초 미만
- 연결: 성공

### 4.3 DynamoDB Global Table 테스트

```powershell
# 1. Tokyo 리전에서 테이블 확인
aws dynamodb describe-table `
  --table-name team_chats_ddb `
  --region ap-northeast-1 `
  --query 'Table.TableStatus'

# 2. 복제 상태 확인
aws dynamodb describe-table `
  --table-name team_chats_ddb `
  --region ap-northeast-1 `
  --query 'Table.Replicas'

# 3. 데이터 동기화 테스트
# Seoul에서 데이터 입력
aws dynamodb put-item `
  --table-name team_chats_ddb `
  --item '{"chat_id": {"S": "test-123"}, "message": {"S": "DR Test"}}' `
  --region ap-northeast-2

# Tokyo에서 데이터 확인 (5초 후)
aws dynamodb get-item `
  --table-name team_chats_ddb `
  --key '{"chat_id": {"S": "test-123"}}' `
  --region ap-northeast-1

# 테스트 데이터 삭제
aws dynamodb delete-item `
  --table-name team_chats_ddb `
  --key '{"chat_id": {"S": "test-123"}}' `
  --region ap-northeast-2
```

**예상 결과:**
- 테이블 상태: `ACTIVE`
- 복제 상태: `ACTIVE`
- 데이터 동기화: 5초 이내

### 4.4 S3 버킷 테스트

```powershell
# 1. DR 버킷 존재 확인
aws s3 ls s3://portforge-front-dr --region ap-northeast-1
aws s3 ls s3://portforge-team-dr --region ap-northeast-1
aws s3 ls s3://portforge-log-dr --region ap-northeast-1

# 2. 파일 업로드/다운로드 테스트
echo "DR Test" > test.txt
aws s3 cp test.txt s3://portforge-team-dr/test.txt --region ap-northeast-1
aws s3 cp s3://portforge-team-dr/test.txt downloaded.txt --region ap-northeast-1
cat downloaded.txt

# 3. 테스트 파일 삭제
aws s3 rm s3://portforge-team-dr/test.txt --region ap-northeast-1
rm test.txt downloaded.txt
```

**예상 결과:**
- 버킷 접근: 성공
- 파일 업로드/다운로드: 성공

### 4.5 ECR 이미지 테스트

```powershell
# 1. Tokyo ECR 리포지토리 확인
aws ecr describe-repositories --region ap-northeast-1

# 2. 이미지 목록 확인
aws ecr list-images `
  --repository-name auth-service `
  --region ap-northeast-1

# 3. 이미지 Pull 테스트
aws ecr get-login-password --region ap-northeast-1 | `
  docker login --username AWS --password-stdin `
  <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com

docker pull <ACCOUNT_ID>.dkr.ecr.ap-northeast-1.amazonaws.com/auth-service:latest
```

**예상 결과:**
- 리포지토리 존재: 7개
- 이미지 존재: latest 태그
- Pull: 성공

### 4.6 Route 53 Health Check 테스트

```powershell
# 1. Health Check 상태 확인
aws route53 list-health-checks --query 'HealthChecks[*].[Id,HealthCheckConfig.FullyQualifiedDomainName]'

# 2. Health Check 상세 상태
aws route53 get-health-check-status --health-check-id <HEALTH_CHECK_ID>
```

**예상 결과:**
- Health Check 상태: `Healthy`

---

## 5. Failover 시뮬레이션 테스트 (분기 1회)

### 5.1 테스트 시나리오
> Seoul 리전 장애 발생 → Tokyo로 자동 Failover

### 5.2 사전 공지
```
[DR 테스트 공지]
- 일시: YYYY-MM-DD HH:MM ~ HH:MM
- 내용: DR Failover 테스트
- 영향: 일시적 서비스 지연 가능
- 담당: DevOps 팀
```

### 5.3 테스트 절차

#### Step 1: 현재 상태 기록
```powershell
# DNS 조회 결과 기록
nslookup api.portforge.org

# Seoul 서비스 상태 확인
curl -s https://api.portforge.org/health

# 현재 시간 기록
Get-Date -Format "yyyy-MM-dd HH:mm:ss"
```

#### Step 2: Primary Health Check 강제 실패
```powershell
# 방법 1: Seoul ALB Target Group에서 모든 타겟 제거 (권장)
# AWS Console > EC2 > Target Groups > 타겟 등록 해제

# 방법 2: Seoul EKS에서 모든 서비스 Pod 중지
kubectl config use-context <SEOUL_CONTEXT>
kubectl scale deployment auth-deployment --replicas=0
kubectl scale deployment project-service --replicas=0
kubectl scale deployment team-service --replicas=0
kubectl scale deployment ai-service --replicas=0
kubectl scale deployment support-deployment --replicas=0
```

#### Step 3: Failover 모니터링
```powershell
# Health Check 상태 모니터링 (30초 간격으로 확인)
while ($true) {
    $status = aws route53 get-health-check-status --health-check-id <ID> --query 'HealthCheckObservations[0].StatusReport.Status' --output text
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "$time - Health Check Status: $status"
    Start-Sleep -Seconds 10
}

# DNS 변경 모니터링
while ($true) {
    $dns = nslookup api.portforge.org 2>$null | Select-String "Address"
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "$time - DNS: $dns"
    Start-Sleep -Seconds 10
}
```

#### Step 4: RDS Promote (수동)
```powershell
# Read Replica를 Primary로 승격
aws rds promote-read-replica `
  --db-instance-identifier portforge-dr-rds-replica `
  --region ap-northeast-1

# 승격 상태 모니터링 (5~10분 소요)
while ($true) {
    $status = aws rds describe-db-instances `
      --db-instance-identifier portforge-dr-rds-replica `
      --region ap-northeast-1 `
      --query 'DBInstances[0].DBInstanceStatus' `
      --output text
    $time = Get-Date -Format "HH:mm:ss"
    Write-Host "$time - RDS Status: $status"
    if ($status -eq "available") { break }
    Start-Sleep -Seconds 30
}
```

#### Step 5: Tokyo 서비스 확인
```powershell
# Tokyo EKS 연결
kubectl config use-context <TOKYO_CONTEXT>

# Pod 상태 확인
kubectl get pods

# 서비스 헬스체크
curl -s https://api.portforge.org/health
```

#### Step 6: 기능 테스트
```powershell
# API 응답 테스트
curl -s https://api.portforge.org/auth/health
curl -s https://api.portforge.org/project/health
curl -s https://api.portforge.org/team/health

# 로그인 테스트 (수동)
# 브라우저에서 https://portforge.org 접속
# 로그인 시도
```

#### Step 7: 결과 기록
| 항목 | 시작 시간 | 완료 시간 | 소요 시간 |
|------|-----------|-----------|-----------|
| Health Check 실패 감지 | | | |
| DNS Failover 완료 | | | |
| RDS Promote 완료 | | | |
| 서비스 정상화 | | | |
| **총 RTO** | | | |

---

## 6. Failback 테스트 (분기 1회)

### 6.1 테스트 시나리오
> Tokyo에서 Seoul로 복귀

### 6.2 테스트 절차

#### Step 1: Seoul 인프라 복구
```powershell
# Seoul EKS Pod 복구
kubectl config use-context <SEOUL_CONTEXT>
kubectl scale deployment auth-deployment --replicas=2
kubectl scale deployment project-service --replicas=2
kubectl scale deployment team-service --replicas=2
kubectl scale deployment ai-service --replicas=2
kubectl scale deployment support-deployment --replicas=1

# Pod 상태 확인
kubectl get pods
```

#### Step 2: Seoul RDS 재구성
```powershell
# 새 Read Replica 생성 (Tokyo → Seoul)
# 또는 백업에서 복원

# 데이터 동기화 확인
# (실제 환경에서는 데이터 정합성 검증 필요)
```

#### Step 3: DNS Failback
```powershell
# Route 53에서 Primary 레코드 활성화
# AWS Console > Route 53 > Hosted Zones > 레코드 수정

# 또는 Health Check 복구로 자동 Failback
```

#### Step 4: Tokyo DR 상태 복원
```powershell
# Tokyo EKS 노드 축소 (필요시)
# Tokyo RDS를 다시 Read Replica로 구성
```

---

## 7. 전체 DR 훈련 (연 1회)

### 7.1 훈련 시나리오
실제 Seoul 리전 장애 상황을 가정한 전체 DR 프로세스 실행

### 7.2 훈련 일정
| 시간 | 활동 |
|------|------|
| T+0 | 장애 발생 알림 |
| T+5분 | 장애 확인 및 DR 결정 |
| T+10분 | Failover 시작 |
| T+30분 | 서비스 복구 확인 |
| T+60분 | 기능 테스트 완료 |
| T+4시간 | Failback 완료 |

### 7.3 역할 분담
| 역할 | 담당자 | 책임 |
|------|--------|------|
| Incident Commander | PM | 전체 조율, 의사결정 |
| DR Lead | DevOps | Failover 실행 |
| DB Admin | DevOps | RDS Promote |
| QA | Backend | 기능 테스트 |
| Communication | PM | 사용자 공지 |

---

## 8. 테스트 체크리스트

### 컴포넌트 테스트
- [ ] EKS 클러스터 상태 확인
- [ ] EKS 노드 상태 확인
- [ ] RDS Read Replica 상태 확인
- [ ] RDS 복제 지연 확인
- [ ] DynamoDB Global Table 상태 확인
- [ ] DynamoDB 데이터 동기화 확인
- [ ] S3 DR 버킷 접근 확인
- [ ] ECR 이미지 존재 확인
- [ ] Route 53 Health Check 상태 확인
- [ ] Secrets Manager 복제 확인

### Failover 테스트
- [ ] Health Check 실패 감지 시간 기록
- [ ] DNS Failover 시간 기록
- [ ] RDS Promote 시간 기록
- [ ] 서비스 복구 시간 기록
- [ ] 총 RTO 계산 및 목표 달성 확인
- [ ] 기능 테스트 통과

### Failback 테스트
- [ ] Seoul 인프라 복구 확인
- [ ] 데이터 정합성 확인
- [ ] DNS Failback 완료
- [ ] Tokyo DR 상태 복원

---

## 9. 테스트 결과 보고서 템플릿

```markdown
# DR 테스트 결과 보고서

## 기본 정보
- 테스트 일시: YYYY-MM-DD HH:MM ~ HH:MM
- 테스트 유형: [컴포넌트/Failover/Failback/전체훈련]
- 참여자: 

## 테스트 결과 요약
| 항목 | 목표 | 실제 | 결과 |
|------|------|------|------|
| RTO | 30분 | XX분 | ✅/❌ |
| RPO | 5초 | XX초 | ✅/❌ |

## 상세 결과
### 성공 항목
- 

### 실패 항목
- 

### 개선 필요 사항
- 

## 다음 단계
- 

## 첨부
- 스크린샷
- 로그 파일
```

---

## 10. 문제 해결 가이드

### Health Check가 Unhealthy로 변경되지 않음
```powershell
# Health Check 설정 확인
aws route53 get-health-check --health-check-id <ID>

# 타겟 엔드포인트 직접 확인
curl -v http://<ALB_DNS>/health
```

### RDS Promote 실패
```powershell
# 에러 로그 확인
aws rds describe-events `
  --source-identifier portforge-dr-rds-replica `
  --source-type db-instance `
  --region ap-northeast-1
```

### DynamoDB 동기화 지연
```powershell
# 복제 상태 상세 확인
aws dynamodb describe-table `
  --table-name team_chats_ddb `
  --region ap-northeast-1 `
  --query 'Table.Replicas'
```

### Tokyo EKS Pod 시작 실패
```powershell
# Pod 상태 확인
kubectl describe pod <POD_NAME>

# 이벤트 확인
kubectl get events --sort-by='.lastTimestamp'

# ECR 이미지 Pull 권한 확인
kubectl describe serviceaccount default
```
