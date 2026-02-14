# Slack 앱 설정 가이드

Infra-Bot을 Slack과 연동하기 위한 Slack API 설정 가이드입니다.

---

## 1. Slack 앱 생성

1. [Slack API](https://api.slack.com/apps) 접속
2. **Create New App** → **From scratch** 선택
3. 앱 이름: `Infra-Bot`, 워크스페이스 선택
4. **Create App** 클릭

---

## 2. Bot Token 발급

1. **OAuth & Permissions** 메뉴 클릭
2. **Scopes** → **Bot Token Scopes**에서 추가:
   - `chat:write`
   - `commands`
   - `channels:read`
3. **Install to Workspace** 클릭
4. **Bot User OAuth Token** 복사 (형식: `xoxb-...`)
5. `secret.yaml`에 토큰 설정

---

## 3. 슬래시 커맨드 등록

**Slash Commands** 메뉴에서 각 커맨드 추가:

| Command | Request URL | Description |
|---------|-------------|-------------|
| `/service-status` | `http://infra-bot.portforge.org/slack/commands` | 서비스 상태 조회 |
| `/health` | `http://infra-bot.portforge.org/slack/commands` | 클러스터 건강검진 |
| `/net-check` | `http://infra-bot.portforge.org/slack/commands` | 네트워크 점검 |
| `/events` | `http://infra-bot.portforge.org/slack/commands` | 인프라 이벤트 |
| `/logs` | `http://infra-bot.portforge.org/slack/commands` | 서비스 로그 조회 |

---

## 4. Interactivity 설정

버튼 클릭 등 인터랙션 처리를 위해 필요합니다.

1. **Interactivity & Shortcuts** 메뉴 클릭
2. **Interactivity** 토글 ON
3. **Request URL** 입력:
   ```
   http://infra-bot.portforge.org/slack/interactions
   ```
4. **Save Changes** 클릭

---

## 5. Grafana 알림 연동

Grafana에서 알림 발생 시 AI 분석을 받으려면:

1. Grafana → **Alerting** → **Contact points**
2. **New contact point** 클릭
3. 설정:
   - **Name**: `Infra-Bot`
   - **Type**: `Webhook`
   - **URL**: `http://infra-bot-service.default.svc/alert`
4. **Save** 클릭
5. Alert Rule에서 Contact point로 `Infra-Bot` 선택

---

## 6. 채널 ID 확인 방법

`configmap.yaml`의 `SLACK_CHANNEL`에는 채널 이름이 아닌 **채널 ID**가 필요합니다.

1. Slack에서 채널 우클릭
2. **채널 세부정보 보기** 클릭
3. 하단에 표시된 ID 복사 (예: `C0A935FLSBH`)

---

## 7. 앱 재설치

권한 변경 후에는 워크스페이스에 앱을 재설치해야 합니다.

1. **Install App** 메뉴 클릭
2. **Reinstall to Workspace** 클릭

---

## 8. HTTPS 설정 (프로덕션 권장)

### Ingress 수정
`ingress.yaml`에 인증서 설정:
```yaml
annotations:
  alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
  alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
  alb.ingress.kubernetes.io/ssl-redirect: '443'
```

### Slack URL 변경
Slack API에서 모든 URL을 `https://`로 변경:
- Slash Commands Request URL
- Interactivity Request URL

---

## 9. 테스트

### Health Check
```bash
curl http://infra-bot.portforge.org/health
# 응답: {"status":"ok"}
```

### Slack에서 테스트
```
/service-status
```
버튼이 표시되면 성공!
