# 📊 Portforge 모니터링 시스템

## 🎯 구성 요소

### **Loki**: 로그 저장 및 인덱싱
- 모든 서비스 로그 중앙 집중 저장
- 빠른 로그 검색 및 필터링

### **Promtail**: 로그 수집 에이전트
- 각 노드에서 파드 로그 자동 수집
- Kubernetes 메타데이터 자동 라벨링

### **Grafana**: 시각화 대시보드
- 실시간 로그 모니터링
- 에러 추적 및 분석
- 비즈니스 메트릭 시각화

## 🚀 설치 방법

### **1. 자동 설치**
```bash
cd k8s/monitoring
chmod +x install-monitoring.sh
./install-monitoring.sh
```

### **2. 수동 설치**
```bash
# 순서대로 실행
kubectl apply -f monitoring-stack.yaml
kubectl apply -f loki-deployment.yaml
kubectl apply -f promtail-daemonset.yaml
kubectl apply -f grafana-deployment.yaml
```

## 📈 대시보드 구성

### **운영 대시보드**
- 전체 서비스 상태
- 에러율 및 응답시간
- HTTP 상태 코드 분석

### **에러 로그 대시보드**
- 실시간 에러 추적
- 서비스별 에러 발생률
- 상세 에러 로그 스트리밍

### **통합 대시보드**
- 운영 + 보안 + 비즈니스 통합
- 5개 핵심 차트
- 중요 이벤트 로그

## 🔧 접속 방법

### **Grafana 접속**
```bash
# 포트포워딩
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# 브라우저에서 접속
http://localhost:3000

# 로그인 정보
사용자명: admin
비밀번호: admin123
```

## 📊 주요 쿼리

### **에러 로그 조회**
```javascript
{app=~"ai-service|auth-service|project-service|team-service|support"} |= "ERROR"
```

### **서비스별 에러율**
```javascript
sum by (app) (rate({app=~".*service"} |= "ERROR"[5m]))
```

### **로그인 활동**
```javascript
{app="auth-service"} |~ "login.*success"
```

## 🛠️ 트러블슈팅

### **파드 상태 확인**
```bash
kubectl get pods -n monitoring
kubectl logs loki-xxx -n monitoring
kubectl logs promtail-xxx -n monitoring
```

### **서비스 연결 확인**
```bash
kubectl port-forward svc/loki 3100:3100 -n monitoring
curl http://localhost:3100/ready
```

### **대시보드 재설정**
```bash
kubectl delete configmap grafana-dashboards -n monitoring
kubectl apply -f monitoring-stack.yaml
kubectl rollout restart deployment/grafana -n monitoring
```

## 📋 모니터링 대상

- **AI Service**: AI 기능 및 모델 호출
- **Auth Service**: 사용자 인증 및 권한
- **Project Service**: 프로젝트 관리
- **Team Service**: 팀 협업 기능
- **Support Service**: 고객 지원 및 커뮤니케이션

## 🎯 알림 설정

에러 발생 시 Slack 알림을 받으려면:
1. Slack Webhook URL 설정
2. AlertManager 구성
3. Grafana 알림 규칙 추가

완전한 실시간 모니터링 시스템으로 서비스 안정성을 보장합니다! 🎉