# DatasourceNoData 알림 트러블슈팅

## 증상
Slack으로 `[INFRA] DatasourceNoData` 알림이 지속적으로 발생

## 초기 의심 원인
- Prometheus 서버 다운
- 네트워크 연결 문제
- Grafana-Prometheus 간 구성 오류

## 실제 원인
Prometheus 서버는 정상 작동 중이었음. 문제는 **TestImageError** 알림 규칙의 설정이었음.

### 알림 규칙 분석
```promql
kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"} > 0
```

이 쿼리는 ImagePullBackOff 상태의 파드를 감지하는데, 현재 클러스터에 해당 상태의 파드가 없어서 쿼리 결과가 비어있음.

알림 규칙의 `noDataState`가 `"NoData"`로 설정되어 있어서, 데이터가 없을 때 "DatasourceNoData" 알림이 발생함.

## 해결 방법

### Grafana UI에서 수정
1. 포트포워딩 실행
   ```powershell
   kubectl port-forward svc/prom-stack-grafana 3000:80
   ```

2. 브라우저에서 http://localhost:3000 접속
   - 로그인: `admin` / `password`

3. Alerting → Alert rules → **TestImageError** 클릭

4. Edit 버튼 클릭

5. 하단 "Configure no data and error handling" 섹션에서
   - "Alert state if no data or all values are null" → **Normal** 선택

6. Save 클릭

## 설정값 설명

| UI 옵션 | API 값 | 동작 |
|---------|--------|------|
| Alerting | Alerting | 데이터 없으면 알림 발생 |
| No Data | NoData | 데이터 없으면 NoData 알림 발생 |
| Normal | OK | 데이터 없으면 정상 상태로 처리 |
| Keep Last State | KeepLast | 이전 상태 유지 |

## 왜 Normal이 적절한가?

- **ImagePullBackOff 파드가 있을 때** → 쿼리 결과 존재 → 알림 발생 ✅
- **ImagePullBackOff 파드가 없을 때** → 쿼리 결과 없음 → Normal 상태 → 알림 안 울림 ✅

"데이터 없음 = 문제 없음"인 경우에 Normal 설정이 적합함.

## 진단 명령어 참고

```powershell
# 모니터링 파드 상태 확인
kubectl get pods -A | Select-String -Pattern "prom|grafana"

# Prometheus 헬스체크
kubectl exec -it prometheus-prom-stack-kube-prometheus-prometheus-0 -c prometheus -- wget -qO- http://localhost:9090/-/healthy

# Grafana 데이터소스 연결 확인
kubectl exec -it <grafana-pod> -c grafana -- curl -s -u admin:password "http://localhost:3000/api/datasources/uid/prometheus/health"

# 현재 알림 상태 확인
kubectl exec -it <grafana-pod> -c grafana -- curl -s -u admin:password "http://localhost:3000/api/alertmanager/grafana/api/v2/alerts"
```

## 날짜
2026-01-24
