# ArgoCD Slack 알림 설정 가이드

## 📋 목차
1. [개요](#개요)
2. [사전 준비사항](#사전-준비사항)
3. [Slack Bot 설정](#slack-bot-설정)
4. [ArgoCD 알림 설정](#argocd-알림-설정)
5. [애플리케이션별 알림 구독](#애플리케이션별-알림-구독)
6. [테스트 및 검증](#테스트-및-검증)
7. [트러블슈팅](#트러블슈팅)

## 개요

이 가이드는 ArgoCD에서 Pod 재생성, 동기화 상태 변경 등의 이벤트가 발생할 때 Slack으로 실시간 알림을 받을 수 있도록 설정하는 방법을 설명합니다.

### 🎯 구현 목표
- Pod 재생성 시 Slack 알림
- 동기화 성공/실패 시 알림
- 애플리케이션 Health 상태 변경 알림
- 한국어 메시지로 직관적인 알림

### 📊 알림 종류
- ✅ **동기화 성공**: 배포 완료 및 Pod 정상 실행
- ❌ **동기화 실패**: 배포 중 오류 발생
- ⚠️ **Health 이상**: 애플리케이션 상태 문제
- 🔄 **동기화 진행중**: 배포 진행 상황

## 사전 준비사항

### 1. 필요한 권한
- Slack 워크스페이스 관리자 권한 (Bot 생성용)
- ArgoCD 관리자 권한 (설정 변경용)
- Kubernetes 클러스터 접근 권한

### 2. 필요한 도구
```bash
# kubectl 설치 확인
kubectl version --client

# ArgoCD CLI 설치 확인 (선택사항)
argocd version --client
```

## Slack Bot 설정

### 1단계: Slack App 생성

1. **Slack API 사이트 접속**
   ```
   https://api.slack.com/apps
   ```

2. **새 앱 생성**
   - "Create New App" 클릭
   - "From scratch" 선택
   - App Name: `ArgoCD Notifications`
   - Workspace: 알림을 받을 워크스페이스 선택

### 2단계: Bot Token 생성

1. **OAuth & Permissions 설정**
   - 좌측 메뉴에서 "OAuth & Permissions" 클릭
   - "Scopes" 섹션에서 "Bot Token Scopes" 추가:
     ```
     chat:write
     chat:write.public
     ```

2. **Bot Token 생성**
   - "Install to Workspace" 클릭
   - 권한 승인 후 "Bot User OAuth Token" 복사
   - 형식: `xoxb-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

### 3단계: 채널 설정

1. **알림 채널 생성** (선택사항)
   ```
   채널명 예시: #argocd-alerts, #deployment-notifications
   ```

2. **Bot을 채널에 초대**
   ```
   /invite @ArgoCD Notifications
   ```

## ArgoCD 알림 설정

### 1단계: Slack Token Secret 생성

```bash
# Slack Bot Token을 Kubernetes Secret으로 생성
kubectl create secret generic argocd-notifications-secret \
  --from-literal=slack-token="xoxb-your-bot-token-here" \
  -n default

# Secret 확인
kubectl get secret argocd-notifications-secret -n default -o yaml
```

### 2단계: ArgoCD Notifications ConfigMap 설정

`argocd-notifications-cm.yaml` 파일 생성:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: default
data:
  # ArgoCD URL 설정
  context: |
    argocdUrl: https://argocd.portforge.org
  
  # Slack 서비스 설정 (Bot Token 방식)
  service.slack: |
    token: $slack-token
  
  # 트리거 설정: Health 상태 이상
  trigger.on-health-degraded: |
    - description: Application has degraded
      send:
      - app-health-degraded
      when: app.status.health.status == 'Degraded'
  
  # 트리거 설정: 동기화 실패
  trigger.on-sync-failed: |
    - description: Application syncing has failed
      send:
      - app-sync-failed
      when: app.status.operationState.phase in ['Error', 'Failed']
  
  # 트리거 설정: 동기화 진행중
  trigger.on-sync-running: |
    - description: Application is being synced
      send:
      - app-sync-running
      when: app.status.operationState != nil and app.status.operationState.phase in ['Running']
  
  # 트리거 설정: 동기화 성공 (Pod 정상 실행)
  trigger.on-sync-succeeded: |
    - description: Application sync completed successfully and is healthy
      send:
      - app-sync-succeeded
      when: app.status.operationState != nil and app.status.operationState.phase in ['Succeeded'] and app.status.operationState.operation.sync != nil and app.status.health.status == 'Healthy'
  
  # 메시지 템플릿: Health 이상
  template.app-health-degraded: |
    message: |
      ⚠️ *{{.app.metadata.name}}* 상태 이상 감지
      
      • Health: {{.app.status.health.status}}
    slack:
      attachments: |
        [{
          "color": "warning",
          "fields": [
            {
              "title": "애플리케이션",
              "value": "{{.app.metadata.name}}",
              "short": true
            },
            {
              "title": "Health 상태",
              "value": "{{.app.status.health.status}}",
              "short": true
            }
          ]
        }]
  
  # 메시지 템플릿: 동기화 실패
  template.app-sync-failed: |
    message: |
      ❌ *{{.app.metadata.name}}* 동기화 실패
      
      • Sync: {{.app.status.sync.status}}
    slack:
      attachments: |
        [{
          "color": "danger",
          "fields": [
            {
              "title": "애플리케이션",
              "value": "{{.app.metadata.name}}",
              "short": true
            },
            {
              "title": "Sync 상태",
              "value": "{{.app.status.sync.status}}",
              "short": true
            }
          ]
        }]
  
  # 메시지 템플릿: 동기화 진행중
  template.app-sync-running: |
    message: |
      🔄 *{{.app.metadata.name}}* 동기화 진행 중
      
      • 단계: {{.app.status.operationState.phase}}
      • 진행률: 동기화 중...
    slack:
      attachments: |
        [{
          "color": "#439FE0",
          "fields": [
            {
              "title": "애플리케이션",
              "value": "{{.app.metadata.name}}",
              "short": true
            },
            {
              "title": "진행 단계",
              "value": "{{.app.status.operationState.phase}}",
              "short": true
            }
          ]
        }]
  
  # 메시지 템플릿: 동기화 성공 (Pod 정상 실행)
  template.app-sync-succeeded: |
    message: |
      🎉 *{{.app.metadata.name}}* 배포 완료!
      
      • 동기화: {{.app.status.sync.status}}
      • 헬스 상태: {{.app.status.health.status}} ✅
      • 이미지 태그: {{.app.status.sync.revision | substr 0 7}}
      
      🚀 모든 Pod가 정상 실행 중입니다!
    slack:
      attachments: |
        [{
          "color": "good",
          "fields": [
            {
              "title": "애플리케이션",
              "value": "{{.app.metadata.name}}",
              "short": true
            },
            {
              "title": "동기화 상태",
              "value": "{{.app.status.sync.status}}",
              "short": true
            },
            {
              "title": "헬스 상태",
              "value": "{{.app.status.health.status}}",
              "short": true
            },
            {
              "title": "이미지 태그",
              "value": "{{.app.status.sync.revision | substr 0 7}}",
              "short": true
            }
          ]
        }]
```

### 3단계: ConfigMap 적용

```bash
# ConfigMap 적용
kubectl apply -f argocd-notifications-cm.yaml

# 적용 확인
kubectl get configmap argocd-notifications-cm -n default -o yaml
```

## 애플리케이션별 알림 구독

각 ArgoCD Application에 알림을 설정하려면 `annotations`를 추가해야 합니다.

### 방법 1: ArgoCD UI에서 설정

1. **ArgoCD 대시보드 접속**
   ```
   https://argocd.portforge.org
   ```

2. **애플리케이션 선택**
   - 알림을 설정할 애플리케이션 클릭

3. **App Details 편집**
   - 상단의 "App Details" 버튼 클릭
   - "Edit" 버튼 클릭

4. **Annotations 추가**
   ```yaml
   # Slack 채널 설정
   notifications.argoproj.io/subscribe.on-sync-succeeded.slack: your-channel-name
   notifications.argoproj.io/subscribe.on-sync-failed.slack: your-channel-name
   notifications.argoproj.io/subscribe.on-health-degraded.slack: your-channel-name
   notifications.argoproj.io/subscribe.on-sync-running.slack: your-channel-name
   ```

### 방법 2: YAML 파일로 설정

각 애플리케이션의 YAML 파일에 annotations 추가:

```yaml
# 예시: k8s/argocd/applications/portforge-support-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: portforge-support-service
  namespace: argocd
  annotations:
    # Slack 알림 구독 설정
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: deployment-notifications
    notifications.argoproj.io/subscribe.on-sync-failed.slack: deployment-notifications
    notifications.argoproj.io/subscribe.on-health-degraded.slack: deployment-notifications
    notifications.argoproj.io/subscribe.on-sync-running.slack: deployment-notifications
spec:
  # ... 기존 설정
```

### 방법 3: kubectl로 직접 설정

```bash
# 애플리케이션에 알림 annotations 추가
kubectl patch application portforge-support-service -n argocd --type merge -p '{
  "metadata": {
    "annotations": {
      "notifications.argoproj.io/subscribe.on-sync-succeeded.slack": "deployment-notifications",
      "notifications.argoproj.io/subscribe.on-sync-failed.slack": "deployment-notifications",
      "notifications.argoproj.io/subscribe.on-health-degraded.slack": "deployment-notifications",
      "notifications.argoproj.io/subscribe.on-sync-running.slack": "deployment-notifications"
    }
  }
}'
```

## 테스트 및 검증

### 1단계: 설정 확인

```bash
# ArgoCD Notifications Controller 로그 확인
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-notifications-controller

# ConfigMap 설정 확인
kubectl get configmap argocd-notifications-cm -n default -o yaml

# Secret 확인
kubectl get secret argocd-notifications-secret -n default
```

### 2단계: 테스트 알림 발송

```bash
# ArgoCD CLI를 사용한 테스트 (선택사항)
argocd admin notifications template notify \
  app-sync-succeeded \
  --recipient slack:your-channel-name
```

### 3단계: 실제 배포로 테스트

1. **애플리케이션 동기화 실행**
   - ArgoCD UI에서 "Sync" 버튼 클릭
   - 또는 kubectl로 강제 동기화:
   ```bash
   kubectl patch application portforge-support-service -n argocd --type merge -p '{
     "operation": {
       "sync": {}
     }
   }'
   ```

2. **Slack 채널에서 알림 확인**
   - 🔄 동기화 진행중 메시지
   - 🎉 배포 완료 메시지

## 트러블슈팅

### 문제 1: 알림이 오지 않음

**원인 및 해결방법:**

1. **Bot Token 확인**
   ```bash
   # Secret 내용 확인
   kubectl get secret argocd-notifications-secret -n default -o jsonpath='{.data.slack-token}' | base64 -d
   ```

2. **채널명 확인**
   - 채널명에 `#` 제외하고 입력
   - 예: `deployment-notifications` (올바름)
   - 예: `#deployment-notifications` (잘못됨)

3. **Bot 권한 확인**
   - Bot이 해당 채널에 초대되었는지 확인
   - Bot에 `chat:write` 권한이 있는지 확인

### 문제 2: 일부 이벤트만 알림 옴

**원인 및 해결방법:**

1. **트리거 조건 확인**
   ```bash
   # ConfigMap의 트리거 설정 확인
   kubectl get configmap argocd-notifications-cm -n default -o yaml
   ```

2. **애플리케이션 상태 확인**
   ```bash
   # 애플리케이션 상태 조회
   kubectl get application portforge-support-service -n argocd -o yaml
   ```

### 문제 3: 메시지 형식이 이상함

**원인 및 해결방법:**

1. **템플릿 문법 확인**
   - Go 템플릿 문법 사용
   - 중괄호 `{{}}` 올바른 사용 확인

2. **JSON 형식 확인**
   - Slack attachments는 유효한 JSON이어야 함
   - 온라인 JSON 검증기로 확인

### 문제 4: ArgoCD Notifications Controller 오류

**해결방법:**

1. **Controller 재시작**
   ```bash
   kubectl rollout restart deployment argocd-notifications-controller -n argocd
   ```

2. **로그 확인**
   ```bash
   kubectl logs -n argocd -l app.kubernetes.io/name=argocd-notifications-controller --tail=100
   ```

## 📚 추가 자료

### 공식 문서
- [ArgoCD Notifications 공식 문서](https://argocd-notifications.readthedocs.io/)
- [Slack API 문서](https://api.slack.com/messaging)

### 유용한 명령어

```bash
# 모든 애플리케이션에 알림 설정 일괄 적용
for app in $(kubectl get applications -n argocd -o name); do
  kubectl patch $app -n argocd --type merge -p '{
    "metadata": {
      "annotations": {
        "notifications.argoproj.io/subscribe.on-sync-succeeded.slack": "deployment-notifications",
        "notifications.argoproj.io/subscribe.on-sync-failed.slack": "deployment-notifications"
      }
    }
  }'
done

# 알림 설정된 애플리케이션 목록 확인
kubectl get applications -n argocd -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.annotations.notifications\.argoproj\.io/subscribe\.on-sync-succeeded\.slack}{"\n"}{end}'
```

### 메시지 커스터마이징

더 상세한 정보를 포함하려면 템플릿을 수정하세요:

```yaml
template.app-sync-succeeded: |
  message: |
    🎉 *{{.app.metadata.name}}* 배포 완료!
    
    📊 **배포 정보**
    • 동기화: {{.app.status.sync.status}}
    • 헬스: {{.app.status.health.status}}
    • 리비전: {{.app.status.sync.revision | substr 0 7}}
    • 배포 시간: {{.app.status.operationState.finishedAt}}
    
    🔗 **링크**
    • [ArgoCD에서 보기]({{.context.argocdUrl}}/applications/{{.app.metadata.name}})
    
    🚀 모든 Pod가 정상 실행 중입니다!
```

---

## ✅ 체크리스트

설정 완료 후 다음 항목들을 확인하세요:

- [ ] Slack Bot Token 생성 및 Secret 등록
- [ ] ArgoCD Notifications ConfigMap 설정
- [ ] 각 애플리케이션에 알림 구독 설정
- [ ] 테스트 배포로 알림 동작 확인
- [ ] 팀원들에게 알림 채널 공유

이제 ArgoCD를 통한 배포 상황을 Slack으로 실시간 모니터링할 수 있습니다! 🎉