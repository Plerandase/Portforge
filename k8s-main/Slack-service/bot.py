"""
Slack Monitoring Bot - Socket Mode
MSA 서비스 모니터링 및 알림 전용 봇
"""
import os
import logging
import time
import re
import schedule
import boto3
import json
from kubernetes import client, config
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests
from datetime import datetime, timedelta

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 변경
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack SDK 로깅도 활성화
logging.getLogger("slack_bolt").setLevel(logging.DEBUG)

# AWS Secret Manager에서 시크릿 가져오기
def get_secrets():
    try:
        client = boto3.client('secretsmanager', region_name='ap-northeast-2')
        response = client.get_secret_value(SecretId='portforge/slack-bot/all-secrets')
        secrets = json.loads(response['SecretString'])
        logger.info("✅ AWS Secret Manager에서 시크릿 로드 완료")
        return secrets
    except Exception as e:
        logger.error(f"❌ Secret Manager 에러: {e}")
        # 환경변수 fallback
        return {
            'SLACK_BOT_TOKEN': os.environ.get("SLACK_BOT_TOKEN"),
            'SLACK_APP_TOKEN': os.environ.get("SLACK_APP_TOKEN"),
            'AWS_ACCESS_KEY_ID': os.environ.get("AWS_ACCESS_KEY_ID"),
            'AWS_SECRET_ACCESS_KEY': os.environ.get("AWS_SECRET_ACCESS_KEY")
        }

# 시크릿 로드
secrets = get_secrets()

# Slack 앱 초기화 (Socket Mode)
app = App(token=secrets['SLACK_BOT_TOKEN'])

# Kubernetes 클라이언트 초기화 (Pod 로그 수집용)
try:
    config.load_incluster_config()  # Pod 내부에서 실행 시
    k8s_v1 = client.CoreV1Api()
    K8S_ENABLED = True
    logger.info("✅ Kubernetes 로그 수집 기능 활성화")
except Exception as e:
    k8s_v1 = None
    K8S_ENABLED = False
    logger.warning(f"⚠️ Kubernetes 로그 수집 비활성화: {e}")

# Bedrock 클라이언트 초기화 (AI 에러 분석용)
try:
    bedrock_client = boto3.client(
        'bedrock-runtime',
        region_name=os.environ.get("BEDROCK_REGION", "us-east-1"),
        aws_access_key_id=secrets['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=secrets['AWS_SECRET_ACCESS_KEY']
    )
    AI_ANALYSIS_ENABLED = True
    logger.info("✅ Bedrock AI 분석 기능 활성화")
except Exception as e:
    bedrock_client = None
    AI_ANALYSIS_ENABLED = False
    logger.warning(f"⚠️ Bedrock AI 분석 비활성화: {e}")

# 알림 채널 설정
ALERT_CHANNEL = os.environ.get("ALERT_CHANNEL", "#alerts")

# MSA 서비스 URL (Kubernetes Service Discovery)
SERVICES = {
    "project": {
        "url": os.environ.get("PROJECT_SERVICE_URL", "http://project-service:8001"),
        "name": "Project 서비스",
        "k8s_deployment": "project-service"  # 실제 deployment 이름
    },
    "team": {
        "url": os.environ.get("TEAM_SERVICE_URL", "http://team-service:8002"),
        "name": "Team 서비스",
        "k8s_deployment": "team-service"  # 실제 deployment 이름
    },
    "ai": {
        "url": os.environ.get("AI_SERVICE_URL", "http://ai-service:8003"),
        "name": "AI 서비스",
        "k8s_deployment": "ai-service"  # 실제 deployment 이름
    },
    "auth": {
        "url": os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000"),
        "name": "Auth 서비스",
        "k8s_deployment": "auth-deployment"  # 실제 deployment 이름 (하드코딩)
    },
    "support": {
        "url": os.environ.get("SUPPORT_SERVICE_URL", "http://support-service:8004"),
        "name": "Support 서비스",
        "k8s_deployment": "support-deployment"  # 실제 deployment 이름 (하드코딩)
    }
}

# 임계값 설정
CPU_THRESHOLD = int(os.environ.get("CPU_THRESHOLD", "80"))
MEMORY_THRESHOLD_PCT = int(os.environ.get("MEMORY_THRESHOLD", "80"))  # 환경변수명 수정
RESPONSE_TIME_THRESHOLD = int(os.environ.get("RESPONSE_TIME_THRESHOLD", "100"))  # 100ms
ERROR_RATE_THRESHOLD = int(os.environ.get("ERROR_RATE_THRESHOLD", "20"))  # 20%로 설정

# Kubernetes 메모리 제한 (Mi 단위)
MEMORY_LIMITS = {
    "auth": 512,      # 512Mi
    "ai": 1024,       # 1Gi
    "team": 1024,     # 1Gi  
    "project": 1024,  # 1Gi
    "support": 512    # 기본값 (deployment에 제한 없음)
}


# ===== 모니터링 함수 =====

def check_service_health(service_key: str, service_info: dict) -> dict:
    """서비스 헬스체크"""
    try:
        url = f"{service_info['url']}/health"
        response = requests.get(url, timeout=5)
        
        return {
            "service": service_info['name'],
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"{service_info['name']} health check failed: {e}")
        return {
            "service": service_info['name'],
            "status": "down",
            "error": str(e)
        }


def get_memory_usage_percentage(service_key: str, current_mb: float) -> float:
    """메모리 사용량을 퍼센티지로 계산"""
    limit_mb = MEMORY_LIMITS.get(service_key, 512)
    return round((current_mb / limit_mb) * 100, 1)


def format_error_rate_with_calculation(metrics_text: str, error_rate: float, total_requests: int) -> str:
    """에러율을 계산식과 함께 표시 (5xx만 에러로 계산)"""
    if total_requests == 0:
        return "에러율: 0% (요청 없음)"
    
    # 4xx, 5xx 요청 수 개별 집계
    error_4xx = 0
    error_5xx = 0
    success_2xx = 0
    
    http_requests = re.findall(r'http_requests_total\{[^}]*status="([^"]+)"[^}]*\}\s+([\d.]+)', metrics_text)
    for status, count in http_requests:
        count = int(float(count))
        if status == "2xx":
            success_2xx += count
        elif status == "4xx":
            error_4xx += count
        elif status == "5xx":
            error_5xx += count
    
    # 5xx만 에러로 계산
    error_total = error_5xx
    
    # 상세 계산식 포함 문자열 생성
    return (f"에러율: {error_rate}% (서버에러 {error_total}건 / 전체 {total_requests}건)\n"
            f"    └ 5xx: {error_5xx}건, 4xx: {error_4xx}건 (클라이언트에러), 2xx: {success_2xx}건")


def check_service_metrics(service_key: str, service_info: dict) -> dict:
    """서비스 메트릭 조회 (Prometheus 형식 파싱)"""
    try:
        url = f"{service_info['url']}/metrics"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            metrics_text = response.text
            parsed_metrics = parse_prometheus_metrics(metrics_text)
            
            return {
                "service": service_info['name'],
                "memory_usage_mb": parsed_metrics.get("memory_usage_mb", 0),
                "cpu_seconds_total": parsed_metrics.get("cpu_seconds_total", 0),
                "error_rate": parsed_metrics.get("error_rate", 0),
                "request_count": parsed_metrics.get("request_count", 0),
                "avg_response_time": parsed_metrics.get("avg_response_time", 0),
                "open_file_descriptors": parsed_metrics.get("open_fds", 0),
                "raw_metrics_text": metrics_text  # 에러율 상세 분석용
            }
    except Exception as e:
        logger.error(f"{service_info['name']} metrics check failed: {e}")
    
    return None


def parse_prometheus_metrics(metrics_text: str) -> dict:
    """Prometheus 텍스트 형식을 파싱하여 주요 메트릭 추출"""
    metrics = {}
    
    # 메모리 사용량 (바이트 → MB 변환)
    memory_match = re.search(r'process_resident_memory_bytes\s+([\d.e+]+)', metrics_text)
    if memory_match:
        memory_bytes = float(memory_match.group(1))
        metrics["memory_usage_mb"] = round(memory_bytes / 1024 / 1024, 1)
    
    # CPU 사용 시간 (총 누적 시간)
    cpu_match = re.search(r'process_cpu_seconds_total\s+([\d.]+)', metrics_text)
    if cpu_match:
        metrics["cpu_seconds_total"] = float(cpu_match.group(1))
    
    # 열린 파일 디스크립터
    fds_match = re.search(r'process_open_fds\s+([\d.]+)', metrics_text)
    if fds_match:
        metrics["open_fds"] = int(float(fds_match.group(1)))
    
    # HTTP 요청 통계로 에러율 계산 (5xx만 에러로 계산)
    total_requests = 0
    error_requests = 0
    
    # 모든 HTTP 요청 수집
    http_requests = re.findall(r'http_requests_total\{[^}]*status="([^"]+)"[^}]*\}\s+([\d.]+)', metrics_text)
    for status, count in http_requests:
        count = float(count)
        total_requests += count
        if status in ["5xx"]:  # 5xx만 에러로 계산 (서버 에러만)
            error_requests += count
    
    if total_requests > 0:
        metrics["error_rate"] = round((error_requests / total_requests) * 100, 2)
        metrics["request_count"] = int(total_requests)
    
    # 평균 응답 시간 계산 (전체 요청 기준)
    duration_sum_match = re.search(r'http_request_duration_histogram_seconds_sum\s+([\d.]+)', metrics_text)
    duration_count_match = re.search(r'http_request_duration_histogram_seconds_count\s+([\d.]+)', metrics_text)
    
    if duration_sum_match and duration_count_match:
        duration_sum = float(duration_sum_match.group(1))
        duration_count = float(duration_count_match.group(1))
        if duration_count > 0:
            metrics["avg_response_time"] = round((duration_sum / duration_count) * 1000, 2)  # ms 단위
    
    return metrics


def analyze_error_patterns(service_key: str, metrics_text: str) -> dict:
    """에러 패턴 분석 및 상세 정보 수집"""
    error_analysis = {
        "4xx_endpoints": [],  # 4xx 에러가 많은 엔드포인트
        "5xx_endpoints": [],  # 5xx 에러가 많은 엔드포인트
        "high_latency_endpoints": [],  # 응답시간이 긴 엔드포인트
        "memory_usage": 0,
        "cpu_usage": 0,
        "total_requests": 0,
        "error_rate": 0
    }
    
    # Prometheus 메트릭에서 엔드포인트별 에러 추출
    # http_requests_total{method="POST", status="4xx", endpoint="/auth/verify-email"} 15
    endpoint_errors = re.findall(r'http_requests_total\{[^}]*endpoint="([^"]+)"[^}]*status="([^"]+)"[^}]*\}\s+([\d.]+)', metrics_text)
    
    for endpoint, status, count in endpoint_errors:
        count = int(float(count))
        if status == "4xx" and count > 5:  # 4xx 에러가 5건 이상
            error_analysis["4xx_endpoints"].append({
                "endpoint": endpoint,
                "count": count
            })
        elif status == "5xx" and count > 0:  # 5xx 에러가 1건 이상
            error_analysis["5xx_endpoints"].append({
                "endpoint": endpoint, 
                "count": count
            })
    
    # 응답시간 분석 (엔드포인트별)
    duration_metrics = re.findall(r'http_request_duration_histogram_seconds_sum\{[^}]*endpoint="([^"]+)"[^}]*\}\s+([\d.]+)', metrics_text)
    duration_counts = re.findall(r'http_request_duration_histogram_seconds_count\{[^}]*endpoint="([^"]+)"[^}]*\}\s+([\d.]+)', metrics_text)
    
    # 엔드포인트별 평균 응답시간 계산
    duration_dict = {endpoint: float(duration) for endpoint, duration in duration_metrics}
    count_dict = {endpoint: float(count) for endpoint, count in duration_counts}
    
    for endpoint in duration_dict:
        if endpoint in count_dict and count_dict[endpoint] > 0:
            avg_duration = (duration_dict[endpoint] / count_dict[endpoint]) * 1000  # ms 단위
            if avg_duration > 500:  # 500ms 이상
                error_analysis["high_latency_endpoints"].append({
                    "endpoint": endpoint,
                    "latency_ms": round(avg_duration, 2)
                })
    
    return error_analysis


def collect_recent_logs(service_key: str, service_info: dict, minutes: int = 10) -> list:
    """Kubernetes API를 통해 최근 로그 수집"""
    if not K8S_ENABLED:
        return []
    
    try:
        deployment_name = service_info.get("k8s_deployment")
        namespace = os.environ.get("K8S_NAMESPACE", "default")
        
        logger.info(f"로그 수집 시도: {deployment_name} in namespace {namespace}")
        
        # 서비스별 라벨 셀렉터 매핑 (하드코딩)
        label_selectors = {
            "auth": "app=auth-service",           # auth-deployment의 라벨
            "support": "app=support",             # support-deployment의 라벨 (수정됨)
            "ai": "app=ai-service",               # ai-service의 라벨
            "team": "app=team-service",           # team-service의 라벨
            "project": "app=project-service"      # project-service의 라벨
        }
        
        label_selector = label_selectors.get(service_key, f"app={deployment_name}")
        
        # Deployment의 Pod 목록 조회
        pods = k8s_v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector
        )
        
        if not pods.items:
            logger.warning(f"No pods found for {deployment_name} with label {label_selector}")
            return []
        
        # 최신 Pod의 로그 수집
        pod_name = pods.items[0].metadata.name
        since_seconds = minutes * 60
        
        logger.info(f"Pod 로그 수집: {pod_name} (최근 {minutes}분)")
        
        # Pod 로그 조회
        log_response = k8s_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            since_seconds=since_seconds,
            tail_lines=50  # 최근 50줄만
        )
        
        # 에러 로그만 필터링
        error_logs = []
        for line in log_response.split('\n'):
            if any(keyword in line.lower() for keyword in ['error', 'exception', 'failed', 'timeout', 'refused', 'denied']):
                error_logs.append(line.strip())
        
        logger.info(f"에러 로그 {len(error_logs)}개 수집됨")
        return error_logs[-10:]  # 최근 10개 에러만
        
    except Exception as e:
        logger.error(f"로그 수집 실패 ({service_key}): {e}")
        return []


def analyze_errors_with_enhanced_context(service_key: str, error_analysis: dict, metrics: dict) -> str:
    """로그 컨텍스트를 포함한 향상된 AI 분석"""
    if not AI_ANALYSIS_ENABLED:
        return "AI 분석 기능이 비활성화되어 있습니다."
    
    # 최근 에러 로그 수집
    recent_logs = collect_recent_logs(service_key, SERVICES[service_key])
    
    # 서비스별 특성을 고려한 프롬프트 구성
    service_context = {
        "auth": "Auth 서비스 - JWT 토큰, 로그인, 회원가입 처리",
        "ai": "AI 서비스 - Bedrock 호출, 테스트 생성, 회의록 작성",
        "project": "Project 서비스 - 프로젝트 CRUD, 지원서 관리",
        "team": "Team 서비스 - 팀 생성, 멤버 관리, 파일 업로드",
        "support": "Support 서비스 - 공지사항, 이벤트, 채팅"
    }
    
    # 실제 deployment 이름 매핑
    deployment_names = {
        "auth": "auth-deployment",
        "support": "support-deployment",
        "ai": "ai-service",
        "team": "team-service", 
        "project": "project-service"
    }
    
    context = service_context.get(service_key, f"{service_key} 서비스")
    deployment_name = deployment_names.get(service_key, f"{service_key}-service")
    
    # 에러율 임계값 체크
    error_rate = metrics.get('error_rate', 0)
    error_status = "정상" if error_rate <= ERROR_RATE_THRESHOLD else f"임계값 초과 (기준: {ERROR_RATE_THRESHOLD}%)"
    
    prompt = f"""당신은 MSA 서비스 장애 분석 전문가입니다.

서비스: {context}
Kubernetes Deployment: {deployment_name}

현재 메트릭:
• 메모리 사용량: {metrics.get('memory_usage_mb', 0)}MB
• 전체 요청 수: {metrics.get('request_count', 0):,}건
• 에러율: {error_rate}% ({error_status})
• 평균 응답시간: {metrics.get('avg_response_time', 0)}ms
• 열린 파일: {metrics.get('open_file_descriptors', 0)}개

문제 엔드포인트:
4xx 에러: {error_analysis.get('4xx_endpoints', [])}
5xx 에러: {error_analysis.get('5xx_endpoints', [])}
높은 지연시간: {error_analysis.get('high_latency_endpoints', [])}

최근 에러 로그 (10분 내):
{chr(10).join(recent_logs) if recent_logs else "에러 로그 없음"}

다음 형식으로 분석해주세요 (마크다운 굵은 글씨 사용 금지):

1. 즉시 확인사항 (5분 내 체크 가능한 kubectl 명령어)
   - kubectl logs deployment/{deployment_name} --tail=100 | grep ERROR
   - kubectl get pods -l app={service_key}-service
   - kubectl describe deployment {deployment_name}

2. 로그 기반 원인 분석
3. 우선순위별 조치 (심각도 순, 구체적 명령어 포함)
4. 모니터링 포인트 (지속 관찰 필요한 메트릭)

분석 마지막에 "위와 같은 분석과 조치사항을 통해..." 같은 불필요한 마무리 문장은 제외해주세요."""

    try:
        # Claude 3 Haiku 호출
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1200,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read())
        diagnosis = response_body['content'][0]['text']
        return diagnosis
        
    except Exception as e:
        logger.error(f"Bedrock 에러 분석 실패: {e}")
        return f"AI 분석 중 오류 발생: {str(e)}"


def send_ai_enhanced_error_alert(service_key: str, service_info: dict, metrics: dict):
    """로그 컨텍스트가 포함된 AI 분석 알림"""
    # 에러 패턴 분석
    error_analysis = analyze_error_patterns(service_key, metrics.get('raw_metrics_text', ''))
    
    # 로그 포함 AI 분석
    ai_diagnosis = analyze_errors_with_enhanced_context(service_key, error_analysis, metrics)
    
    # 최근 에러 로그 수집
    recent_logs = collect_recent_logs(service_key, service_info, minutes=5)
    
    # 스마트 알림 메시지 구성
    alert_message = f"""🚨 {service_info['name']} 에러 발생 + AI 분석

현재 상황:
• 에러율: {metrics['error_rate']}% (임계값: {ERROR_RATE_THRESHOLD}%)
• 총 요청: {metrics['request_count']:,}건
• 메모리: {get_memory_usage_percentage(service_key, metrics['memory_usage_mb'])}%
• 평균 응답시간: {metrics['avg_response_time']}ms

문제 엔드포인트:"""
    
    # 5xx 에러 상세 (우선순위)
    if error_analysis.get('5xx_endpoints'):
        for error in error_analysis.get('5xx_endpoints', [])[:3]:  # 상위 3개만
            alert_message += f"\n• {error['endpoint']}: {error['count']}건 (5xx)"
    
    # 4xx 에러 상세
    if error_analysis.get('4xx_endpoints'):
        for error in error_analysis.get('4xx_endpoints', [])[:2]:  # 상위 2개만
            alert_message += f"\n• {error['endpoint']}: {error['count']}건 (4xx)"
    
    # 높은 지연시간 엔드포인트
    if error_analysis.get('high_latency_endpoints'):
        for latency in error_analysis.get('high_latency_endpoints', [])[:2]:  # 상위 2개만
            alert_message += f"\n• {latency['endpoint']}: {latency['latency_ms']}ms (지연)"
    
    if not any([error_analysis.get('5xx_endpoints'), error_analysis.get('4xx_endpoints'), error_analysis.get('high_latency_endpoints')]):
        alert_message += "\n• 엔드포인트별 상세 정보 없음"
    
    # 최근 에러 로그 (간략히)
    if recent_logs:
        alert_message += f"\n\n최근 에러 로그 (5분 내):"
        for log in recent_logs[:3]:  # 최근 3개만
            # 로그가 너무 길면 자르기
            short_log = log[:100] + "..." if len(log) > 100 else log
            alert_message += f"\n• {short_log}"
    
    # AI 진단 결과
    alert_message += f"""

AI 진단 결과:
{ai_diagnosis}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    send_alert(alert_message, severity="critical")


def send_alert(message: str, severity: str = "info"):
    """Slack 알림 전송"""
    emoji = {
        "critical": "🔴",
        "warning": "⚠️",
        "info": "ℹ️",
        "success": "✅"
    }.get(severity, "📢")
    
    try:
        app.client.chat_postMessage(
            channel=ALERT_CHANNEL,
            text=f"{emoji} {message}",
            unfurl_links=False,
            unfurl_media=False
        )
        logger.info(f"Alert sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")


# ===== 주기적 모니터링 작업 =====

def monitor_resources():
    """리소스 사용률 모니터링 (5분마다) - 퍼센티지 기반"""
    logger.info("Checking resource usage...")
    
    for service_key, service_info in SERVICES.items():
        metrics = check_service_metrics(service_key, service_info)
        
        if metrics:
            # 메모리 퍼센티지 체크
            memory_mb = metrics["memory_usage_mb"]
            memory_pct = get_memory_usage_percentage(service_key, memory_mb)
            memory_limit = MEMORY_LIMITS.get(service_key, 512)
            
            if memory_pct > MEMORY_THRESHOLD_PCT:
                send_alert(
                    f"{metrics['service']} 메모리 {memory_pct}% "
                    f"({memory_mb}MB / {memory_limit}MB) "
                    f"임계값: {MEMORY_THRESHOLD_PCT}%",
                    severity="warning"
                )
            
            # 에러율 체크 - AI 분석 포함
            if metrics["error_rate"] > ERROR_RATE_THRESHOLD:
                if AI_ANALYSIS_ENABLED:
                    send_ai_enhanced_error_alert(service_key, service_info, metrics)
                else:
                    # 기존 알림 (AI 없이)
                    error_detail = format_error_rate_with_calculation(
                        metrics.get('raw_metrics_text', ''), 
                        metrics['error_rate'], 
                        metrics['request_count']
                    )
                    send_alert(
                        f"{metrics['service']} 에러율 {metrics['error_rate']}% "
                        f"(임계값: {ERROR_RATE_THRESHOLD}%)\n{error_detail}",
                        severity="critical"
                    )
            
            # 응답 시간 체크
            if metrics["avg_response_time"] > RESPONSE_TIME_THRESHOLD:
                send_alert(
                    f"{metrics['service']} 평균 응답시간 {metrics['avg_response_time']}ms "
                    f"(임계값: {RESPONSE_TIME_THRESHOLD}ms)",
                    severity="warning"
                )


def monitor_health():
    """서비스 헬스 모니터링 (1분마다)"""
    logger.info("Checking service health...")
    
    for service_key, service_info in SERVICES.items():
        health = check_service_health(service_key, service_info)
        
        if health["status"] == "down":
            send_alert(
                f"{health['service']} 서비스 다운! 에러: {health.get('error', 'Unknown')}",
                severity="critical"
            )
        elif health["status"] == "unhealthy":
            send_alert(
                f"{health['service']} 서비스 비정상 (HTTP {health['status_code']})",
                severity="warning"
            )


# ===== Slack 이벤트 핸들러 =====

@app.event("app_mention")
def handle_mention(event, say):
    """봇 멘션 처리"""
    logger.info(f"🎯 멘션 이벤트 수신: {event}")
    try:
        text = event.get("text", "").lower()
        logger.info(f"📝 수신된 텍스트: {text}")
        
        if "상태" in text or "status" in text:
            logger.info("상태 명령어 처리 중...")
            response = get_all_status()
        elif "헬프" in text or "help" in text:
            logger.info("도움말 명령어 처리 중...")
            response = get_help_message()
        elif "메트릭" in text or "metrics" in text:
            logger.info("메트릭 명령어 처리 중...")
            response = get_all_metrics()
        else:
            logger.info("기본 응답 처리 중...")
            response = "무엇을 도와드릴까요? 'help'를 입력하면 사용 가능한 명령어를 확인할 수 있습니다."
        
        logger.info(f"📤 응답 전송 중: {len(response)} 문자")
        say(response)
        logger.info("✅ 응답 전송 완료")
        
    except Exception as e:
        logger.error(f"❌ 멘션 처리 중 오류: {e}", exc_info=True)
        say(f"오류가 발생했습니다: {str(e)}")


def get_all_status() -> str:
    """모든 서비스 상태 조회"""
    result = f"📊 *서비스 상태 리포트* ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n"
    
    for service_key, service_info in SERVICES.items():
        health = check_service_health(service_key, service_info)
        
        status_emoji = {
            "healthy": "✅",
            "unhealthy": "⚠️",
            "down": "🔴"
        }.get(health["status"], "❓")
        
        result += f"{status_emoji} *{health['service']}*\n"
        result += f"  상태: {health['status']}\n"
        
        if health["status"] == "healthy":
            result += f"  응답시간: {health['response_time']:.2f}초\n"
        elif "error" in health:
            result += f"  에러: {health['error']}\n"
        
        result += "\n"
    
    return result


def get_all_metrics() -> str:
    """모든 서비스 메트릭 조회 (향상된 버전 + 시간 정보)"""
    current_time = datetime.now()
    result = f"📈 *서비스 메트릭 리포트* ({current_time.strftime('%Y-%m-%d %H:%M:%S')})\n\n"
    
    for service_key, service_info in SERVICES.items():
        metrics = check_service_metrics(service_key, service_info)
        
        if metrics:
            # 메모리 퍼센티지 계산
            memory_mb = metrics['memory_usage_mb']
            memory_pct = get_memory_usage_percentage(service_key, memory_mb)
            memory_limit = MEMORY_LIMITS.get(service_key, 512)
            
            # 에러율 상세 정보
            error_detail = format_error_rate_with_calculation(
                metrics.get('raw_metrics_text', ''), 
                metrics['error_rate'], 
                metrics['request_count']
            )
            
            # 상태 아이콘 결정
            status_icon = "🔴" if memory_pct > 90 else "⚠️" if memory_pct > 80 else "✅"
            
            # CPU 사용률 추정 (누적 시간 기반)
            cpu_total = metrics['cpu_seconds_total']
            uptime_estimate = "알 수 없음"
            if cpu_total > 0:
                # 대략적인 업타임 추정 (CPU 시간 / 코어 수)
                estimated_uptime_hours = cpu_total / 0.5  # 0.5 코어 기준
                if estimated_uptime_hours < 24:
                    uptime_estimate = f"{estimated_uptime_hours:.1f}시간"
                else:
                    uptime_estimate = f"{estimated_uptime_hours/24:.1f}일"
            
            result += f"*{metrics['service']}*\n"
            result += f"  메모리: {memory_mb}MB ({memory_pct}% / {memory_limit}MB 제한)\n"
            result += f"  {error_detail}\n"
            result += f"  요청 수: {metrics['request_count']:,} (서비스 시작부터 누적)\n"
            result += f"  평균 응답시간: {metrics['avg_response_time']}ms\n"
            result += f"  열린 파일: {metrics['open_file_descriptors']}\n"
            result += f"  CPU 누적시간: {metrics['cpu_seconds_total']}초 (추정 업타임: {uptime_estimate})\n"
            result += f"  상태: {status_icon}\n\n"
        else:
            result += f"*{service_info['name']}*\n"
            result += f"  메트릭 조회 실패 ❌\n\n"
    
    result += f"\n💡 *참고사항:*\n"
    result += f"• 요청 수는 서비스 시작부터의 누적값입니다\n"
    result += f"• Pod 재시작 시 카운터가 0으로 리셋됩니다\n"
    result += f"• 현재 시점 기준 스냅샷 데이터입니다 (히스토리 없음)\n"
    result += f"• 더 정확한 트렌드 분석은 Grafana를 이용하세요: https://grafana.portforge.org"
    
    return result


def get_help_message() -> str:
    """도움말"""
    return f"""
🤖 *PortForge 모니터링 봇*

*사용 가능한 명령어:*

📊 상태 확인:
  • @bot 상태 - 모든 서비스 상태 조회
  • @bot status - 모든 서비스 상태 조회

📈 메트릭 확인:
  • @bot 메트릭 - 모든 서비스 메트릭 조회 (퍼센티지 + 상세 에러율)
  • @bot metrics - 모든 서비스 메트릭 조회

❓ 도움말:
  • @bot help - 이 도움말 표시

*자동 알림 임계값:*
• 메모리 사용량: {MEMORY_THRESHOLD_PCT}% (Kubernetes 제한 기준)
• 응답시간: {RESPONSE_TIME_THRESHOLD}ms 초과 시 자동 알림
• 에러율: {ERROR_RATE_THRESHOLD}% 초과 시 자동 알림 (5xx 서버에러만)
• 서비스 다운 시 즉시 알림

*메모리 제한 설정:*
• Auth: {MEMORY_LIMITS['auth']}MB
• AI: {MEMORY_LIMITS['ai']}MB  
• Team: {MEMORY_LIMITS['team']}MB
• Project: {MEMORY_LIMITS['project']}MB
• Support: {MEMORY_LIMITS['support']}MB

*알림 채널:* {ALERT_CHANNEL}

*AI 분석:* {"✅ 활성화 (Bedrock)" if AI_ANALYSIS_ENABLED else "❌ 비활성화"}
*로그 수집:* {"✅ 활성화 (Kubernetes)" if K8S_ENABLED else "❌ 비활성화"}
"""


@app.event("message")
def handle_message_events(body, logger):
    """일반 메시지 이벤트"""
    logger.debug(f"📨 메시지 이벤트 수신: {body}")


# 모든 이벤트 로깅 (디버그용)
@app.event(".*")
def handle_all_events(event, logger):
    """모든 이벤트 로깅 (디버그용)"""
    event_type = event.get('type', 'unknown')
    logger.info(f"🔔 이벤트 수신: {event_type}")
    if event_type == 'app_mention':
        logger.info(f"🎯 멘션 이벤트 상세: {event}")


# ===== 스케줄러 설정 =====

def run_scheduler():
    """백그라운드 스케줄러 실행"""
    # 1분마다 헬스체크
    schedule.every(1).minutes.do(monitor_health)
    
    # 5분마다 리소스 체크
    schedule.every(5).minutes.do(monitor_resources)
    
    logger.info("Scheduler started")
    
    while True:
        schedule.run_pending()
        time.sleep(1)


# ===== 메인 실행 =====

if __name__ == "__main__":
    import threading
    
    # 스케줄러를 별도 스레드로 실행
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Socket Mode Handler 시작
    handler = SocketModeHandler(app, secrets['SLACK_APP_TOKEN'])
    
    logger.info("⚡️ Slack Monitoring Bot starting in Socket Mode...")
    logger.info(f"Alert Channel: {ALERT_CHANNEL}")
    logger.info(f"Monitoring Services: {list(SERVICES.keys())}")
    logger.info(f"Thresholds - Memory: {MEMORY_THRESHOLD_PCT}% (percentage-based), Error Rate: {ERROR_RATE_THRESHOLD}%, Response Time: {RESPONSE_TIME_THRESHOLD}ms")
    logger.info(f"AI Analysis: {'Enabled (Bedrock)' if AI_ANALYSIS_ENABLED else 'Disabled'}")
    logger.info(f"Log Collection: {'Enabled (Kubernetes)' if K8S_ENABLED else 'Disabled'}")
    
    # 시작 알림
    start_message = "모니터링 봇이 시작되었습니다."
    if AI_ANALYSIS_ENABLED:
        start_message += " (AI 에러 분석 활성화)"
    if K8S_ENABLED:
        start_message += " (로그 수집 활성화)"
    send_alert(start_message, severity="success")
    
    handler.start()
