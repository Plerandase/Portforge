# External Secrets 설정 가이드

기존 secret.yaml의 민감정보를 AWS Secrets Manager로 이전하고, External Secrets Operator로 관리합니다.

## 폴더 구조

```
external-secrets/
├── kr/          # 한국 리전 (ap-northeast-2)
├── dr/          # 일본 DR 리전 (ap-northeast-1)
└── common/      # 공통 설정 (operator, IAM 정책)
```

## 개요

```
Secrets Manager → External Secrets Operator → K8s Secret → Pod
```

K8s Secret 이름이 동일하므로 Deployment 수정 불필요합니다.

## 현재 상태

✅ External Secrets Operator 설치 완료 (default 네임스페이스)
✅ ClusterSecretStore 생성 완료
✅ 8개 ExternalSecret 배포 완료
✅ 기존 secret.yaml 파일 삭제 완료

## Secrets Manager 시크릿 구조

| 시크릿 이름 | K8s Secret 이름 | 서비스 |
|-------------|-----------------|--------|
| `portforge/auth-service` | `auth-service-secrets` | Auth |
| `portforge/ai-service` | `ai-service-secrets` | AI |
| `portforge/team-service` | `team-service-secrets` | Team |
| `portforge/project-service` | `project-service-secrets` | Project |
| `portforge/support-service` | `support-secret` | Support |
| `portforge/slack-infra-bot` | `infrabot-secret` | Slack Infra Bot |
| `portforge/slack-service-bot` | `slack-bot-secret` | Slack Service Bot |
| `portforge/argocd-notifications` | `argocd-notifications-secret` | ArgoCD |

## 적용 방법

### 한국 리전 (KR)
```powershell
kubectl apply -f k8s/external-secrets/common/
kubectl apply -f k8s/external-secrets/kr/
```

### 일본 DR 리전
```powershell
kubectl apply -f k8s/external-secrets/common/
kubectl apply -f k8s/external-secrets/dr/
```

## 시크릿 값 변경 방법

```powershell
# 예: AI 서비스 DB 비밀번호 변경
aws secretsmanager update-secret `
  --secret-id "portforge/ai-service" `
  --secret-string '{"database-url":"새값","db-host":"새값",...}' `
  --region ap-northeast-2

# K8s Secret 즉시 동기화 (기본 1시간 주기)
kubectl annotate externalsecret ai-service-secrets force-sync=$(date +%s) --overwrite
```

## 상태 확인

```powershell
kubectl get externalsecrets
kubectl get clustersecretstore
kubectl get secrets
```
