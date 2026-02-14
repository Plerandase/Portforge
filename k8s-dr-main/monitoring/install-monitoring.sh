#!/bin/bash

echo "🚀 Portforge 모니터링 시스템 설치 시작..."

# 1. 네임스페이스 생성
echo "📁 모니터링 네임스페이스 생성..."
kubectl apply -f monitoring-stack.yaml

# 2. Loki 배포
echo "📊 Loki 로그 저장소 배포..."
kubectl apply -f loki-deployment.yaml

# 3. Promtail 배포
echo "📡 Promtail 로그 수집기 배포..."
kubectl apply -f promtail-daemonset.yaml

# 4. Grafana 배포
echo "📈 Grafana 대시보드 배포..."
kubectl apply -f grafana-deployment.yaml

# 5. 배포 상태 확인
echo "⏳ 배포 상태 확인 중..."
kubectl rollout status deployment/loki -n monitoring
kubectl rollout status deployment/grafana -n monitoring
kubectl rollout status daemonset/promtail -n monitoring

# 6. 서비스 상태 확인
echo "✅ 서비스 상태:"
kubectl get pods -n monitoring
kubectl get svc -n monitoring

echo "🎉 모니터링 시스템 설치 완료!"
echo ""
echo "📋 접속 정보:"
echo "Grafana URL: http://localhost:3000 (포트포워딩 필요)"
echo "사용자명: admin"
echo "비밀번호: admin123"
echo ""
echo "🔗 포트포워딩 명령어:"
echo "kubectl port-forward svc/grafana 3000:3000 -n monitoring"