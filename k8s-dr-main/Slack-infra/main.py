import os
import json
import logging
import boto3
import requests
import threading
import time
import socket
from fastapi import FastAPI, Request, BackgroundTasks, Form
from tenacity import retry, stop_after_attempt, wait_fixed
from kubernetes import client, config
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("infra-bot")

app = FastAPI()

# 환경 변수 (Kubernetes Secret에서 주입됨)
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1") # Bedrock 사용 리전
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "default")
DAILY_REPORT_ENABLED = os.getenv("DAILY_REPORT_ENABLED", "false").lower() == "true"
DAILY_REPORT_TZ = os.getenv("DAILY_REPORT_TZ", "Asia/Seoul")
DAILY_REPORT_WINDOW_MINUTES = int(os.getenv("DAILY_REPORT_WINDOW_MINUTES", "5"))
DAILY_REPORT_HOURS = os.getenv("DAILY_REPORT_HOURS", "9")
DAILY_REPORT_LEASE = os.getenv("DAILY_REPORT_LEASE", "infra-bot-daily-report")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prom-stack-kube-prometheus-prometheus.default.svc:9090")
RDS_ENDPOINT = os.getenv("RDS_ENDPOINT", "")
RDS_PORT = int(os.getenv("RDS_PORT", "5432"))
S3_BUCKET = os.getenv("S3_BUCKET", "")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "")
AWS_RESOURCE_REGION = os.getenv("AWS_RESOURCE_REGION", "ap-northeast-2")

# AWS Bedrock 클라이언트
bedrock = boto3.client(service_name='bedrock-runtime', region_name=AWS_REGION)

# Kubernetes 클라이언트 초기화
try:
    config.load_incluster_config()  # Pod 내부에서 실행 시
except:
    config.load_kube_config()  # 로컬 개발 시
k8s_apps_v1 = client.AppsV1Api()
k8s_core_v1 = client.CoreV1Api()
k8s_custom = client.CustomObjectsApi()
k8s_coord = client.CoordinationV1Api()

# 서비스 매핑 (deployment 이름)
SERVICES = {
    "Auth": "auth-deployment",
    "AI": "ai-service",
    "Project": "project-service",
    "Team": "team-service",
    "Support": "support-deployment"
}

ACTIVE_ALERTS = {}

# Slack attachment colors
COLOR_CRITICAL = "#E01E5A"
COLOR_WARNING = "#ECB22E"
COLOR_RESOLVED = "#2EB67D"

def parse_k8s_quantity(value: str) -> float:
    """Parse Kubernetes quantity strings into base units."""
    if value is None:
        return 0.0
    value = str(value).strip()
    if not value:
        return 0.0
    units = {
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "": 1.0,
        "Ki": 1024.0,
        "Mi": 1024.0 ** 2,
        "Gi": 1024.0 ** 3,
        "Ti": 1024.0 ** 4,
        "Pi": 1024.0 ** 5,
        "Ei": 1024.0 ** 6,
        "K": 1000.0,
        "M": 1000.0 ** 2,
        "G": 1000.0 ** 3,
        "T": 1000.0 ** 4,
        "P": 1000.0 ** 5,
        "E": 1000.0 ** 6,
    }
    for suffix in ["Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "n", "u", "m", "K", "M", "G", "T", "P", "E"]:
        if value.endswith(suffix):
            number = value[: -len(suffix)].strip()
            try:
                return float(number) * units[suffix]
            except ValueError:
                return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0

def format_bytes_per_sec(value: float) -> str:
    """Format bytes per second into human readable string."""
    if value is None:
        return "n/a"
    units = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]
    v = float(value)
    idx = 0
    while v >= 1024 and idx < len(units) - 1:
        v /= 1024.0
        idx += 1
    return f"{v:.1f} {units[idx]}"

def query_prometheus(expr: str):
    """Query Prometheus instant vector."""
    try:
        resp = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": expr},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            return None
        result = data.get("data", {}).get("result", [])
        if not result:
            return None
        value = result[0].get("value", [None, None])[1]
        return float(value)
    except Exception as e:
        logger.warning(f"Prometheus query failed ({expr}): {e}")
        return None

def get_prometheus_io_summary():
    """Get disk and network I/O summary from Prometheus."""
    disk_read = query_prometheus("sum(rate(node_disk_read_bytes_total[5m]))")
    disk_write = query_prometheus("sum(rate(node_disk_written_bytes_total[5m]))")
    net_rx = query_prometheus("sum(rate(node_network_receive_bytes_total[5m]))")
    net_tx = query_prometheus("sum(rate(node_network_transmit_bytes_total[5m]))")
    return {
        "disk_read": disk_read,
        "disk_write": disk_write,
        "net_rx": net_rx,
        "net_tx": net_tx,
    }

def check_tcp(host: str, port: int, timeout: float = 3.0):
    """Check TCP connectivity."""
    try:
        socket.getaddrinfo(host, port)
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except Exception as e:
        return False, str(e)

def find_services_for_deployment(deployment):
    """Find services whose selectors match deployment pod labels."""
    labels = deployment.spec.selector.match_labels or {}
    if not labels:
        return []
    services = k8s_core_v1.list_namespaced_service(namespace=K8S_NAMESPACE).items
    matched = []
    for svc in services:
        selector = svc.spec.selector or {}
        if not selector:
            continue
        if all(labels.get(k) == v for k, v in selector.items()):
            matched.append(svc)
    return matched

def check_microservices_connectivity():
    """Check microservice readiness and service endpoints."""
    results = []
    for svc_name, deployment_name in SERVICES.items():
        try:
            deployment, pods = get_deployment_pods(deployment_name)
            ready = 0
            for pod in pods:
                if pod.status.conditions:
                    for cond in pod.status.conditions:
                        if cond.type == "Ready" and cond.status == "True":
                            ready += 1
                            break
            services = find_services_for_deployment(deployment)
            endpoints_ok = False
            endpoint_count = 0
            svc_names = []
            for svc in services:
                svc_names.append(svc.metadata.name)
                ep = k8s_core_v1.read_namespaced_endpoints(
                    name=svc.metadata.name,
                    namespace=K8S_NAMESPACE
                )
                subsets = ep.subsets or []
                for subset in subsets:
                    addresses = subset.addresses or []
                    endpoint_count += len(addresses)
            if endpoint_count > 0:
                endpoints_ok = True

            status = "ok"
            if ready == 0:
                status = "critical"
            elif not endpoints_ok:
                status = "warning"
            results.append({
                "service": svc_name,
                "deployment": deployment_name,
                "ready": ready,
                "replicas": deployment.spec.replicas or 0,
                "services": svc_names,
                "endpoints": endpoint_count,
                "status": status
            })
        except Exception as e:
            results.append({
                "service": svc_name,
                "deployment": deployment_name,
                "ready": 0,
                "replicas": 0,
                "services": [],
                "endpoints": 0,
                "status": "critical",
                "error": str(e)
            })
    return results

def check_aws_resources():
    """Check connectivity to AWS core resources."""
    results = []
    if RDS_ENDPOINT:
        ok, err = check_tcp(RDS_ENDPOINT, RDS_PORT)
        results.append({
            "name": "RDS",
            "target": f"{RDS_ENDPOINT}:{RDS_PORT}",
            "status": "ok" if ok else "critical",
            "error": "" if ok else err
        })
    else:
        results.append({"name": "RDS", "target": "not set", "status": "warning", "error": "skipped"})

    if S3_BUCKET:
        try:
            s3 = boto3.client("s3", region_name=AWS_RESOURCE_REGION)
            s3.head_bucket(Bucket=S3_BUCKET)
            results.append({"name": "S3", "target": S3_BUCKET, "status": "ok", "error": ""})
        except Exception as e:
            results.append({"name": "S3", "target": S3_BUCKET, "status": "critical", "error": str(e)})
    else:
        results.append({"name": "S3", "target": "not set", "status": "warning", "error": "skipped"})

    if DYNAMODB_TABLE:
        try:
            dynamo = boto3.client("dynamodb", region_name=AWS_RESOURCE_REGION)
            dynamo.describe_table(TableName=DYNAMODB_TABLE)
            results.append({"name": "DynamoDB", "target": DYNAMODB_TABLE, "status": "ok", "error": ""})
        except Exception as e:
            results.append({"name": "DynamoDB", "target": DYNAMODB_TABLE, "status": "critical", "error": str(e)})
    else:
        results.append({"name": "DynamoDB", "target": "not set", "status": "warning", "error": "skipped"})

    return results

def format_net_check_message(ms_results: list, aws_results: list):
    """Format net check results for Slack."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔌 네트워크 점검"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*마이크로서비스 통신 점검*"}
        }
    ]
    for r in ms_results:
        if r.get("status") == "critical":
            icon = "❌"
        elif r.get("status") == "warning":
            icon = "⚠️"
        else:
            icon = "✅"
        svc_list = ", ".join(r.get("services") or [])
        detail = f"{icon} *{r['service']}* (ready {r['ready']}/{r['replicas']})"
        if svc_list:
            detail += f" / svc: `{svc_list}` / endpoints: {r['endpoints']}"
        if r.get("error"):
            detail += f" / error: {r['error']}"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": detail}
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*AWS 리소스 점검*"}
    })
    for r in aws_results:
        if r.get("status") == "critical":
            icon = "❌"
        elif r.get("status") == "warning":
            icon = "⚠️"
        else:
            icon = "✅"
        detail = f"{icon} *{r['name']}* `{r['target']}`"
        if r.get("error") and r.get("error") != "skipped":
            detail += f" / error: {r['error']}"
        elif r.get("error") == "skipped":
            detail += " / skipped (not configured)"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": detail}
        })
    return blocks

def update_alert_cache(alerts: list):
    """Update in-memory active alert cache."""
    for alert in alerts:
        status = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        fingerprint = (
            alert.get("fingerprint")
            or f"{labels.get('alertname','unknown')}|{labels.get('instance','')}|{labels.get('pod','')}"
        )
        if status == "resolved":
            ACTIVE_ALERTS.pop(fingerprint, None)
            continue
        ACTIVE_ALERTS[fingerprint] = {
            "name": labels.get("alertname", "unknown"),
            "severity": labels.get("severity", "n/a"),
            "summary": annotations.get("summary") or annotations.get("description") or annotations.get("message") or "",
            "startsAt": alert.get("startsAt", ""),
        }

def get_node_health_summary():
    """Get node readiness and cluster resource usage."""
    nodes = k8s_core_v1.list_node().items
    ready = 0
    for node in nodes:
        conditions = node.status.conditions or []
        for cond in conditions:
            if cond.type == "Ready" and cond.status == "True":
                ready += 1
                break
    total = len(nodes)
    not_ready = total - ready

    cpu_usage = None
    mem_usage = None
    try:
        metrics = k8s_custom.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )
        usage_map = {item["metadata"]["name"]: item["usage"] for item in metrics.get("items", [])}
        total_cpu_usage = 0.0
        total_mem_usage = 0.0
        total_cpu_capacity = 0.0
        total_mem_capacity = 0.0
        for node in nodes:
            name = node.metadata.name
            capacity = node.status.capacity or {}
            total_cpu_capacity += parse_k8s_quantity(capacity.get("cpu", "0"))
            total_mem_capacity += parse_k8s_quantity(capacity.get("memory", "0"))
            usage = usage_map.get(name, {})
            total_cpu_usage += parse_k8s_quantity(usage.get("cpu", "0"))
            total_mem_usage += parse_k8s_quantity(usage.get("memory", "0"))
        if total_cpu_capacity > 0:
            cpu_usage = (total_cpu_usage / total_cpu_capacity) * 100.0
        if total_mem_capacity > 0:
            mem_usage = (total_mem_usage / total_mem_capacity) * 100.0
    except Exception as e:
        logger.warning(f"Metrics API not available: {e}")

    return {
        "ready": ready,
        "not_ready": not_ready,
        "total": total,
        "cpu_usage": cpu_usage,
        "mem_usage": mem_usage,
    }

def get_pod_summary():
    """Get pod phase summary across the cluster."""
    pods = k8s_core_v1.list_pod_for_all_namespaces().items
    running = 0
    pending = 0
    error = 0
    error_reasons = {
        "CrashLoopBackOff",
        "Error",
        "ImagePullBackOff",
        "ErrImagePull",
        "CreateContainerConfigError",
        "RunContainerError",
    }
    for pod in pods:
        phase = pod.status.phase or "Unknown"
        has_error = False
        container_statuses = pod.status.container_statuses or []
        for container in container_statuses:
            state = container.state
            if state and state.waiting and state.waiting.reason in error_reasons:
                has_error = True
                break
        if has_error or phase in ["Failed", "Unknown"]:
            error += 1
        elif phase == "Pending":
            pending += 1
        elif phase == "Running":
            running += 1
    return {
        "running": running,
        "pending": pending,
        "error": error,
    }

def get_active_alerts(limit: int = 5):
    """Return a list of active alerts."""
    alerts = list(ACTIVE_ALERTS.values())
    def sort_key(item):
        try:
            return datetime.fromisoformat(item.get("startsAt", "").replace("Z", "+00:00"))
        except Exception:
            return datetime.min
    alerts.sort(key=sort_key, reverse=True)
    return alerts[:limit]

def build_health_snapshot():
    """Collect cluster health data."""
    node_summary = get_node_health_summary()
    pod_summary = get_pod_summary()
    io_summary = get_prometheus_io_summary()
    alerts = get_active_alerts(limit=5)
    return node_summary, pod_summary, io_summary, alerts

def summarize_health_with_bedrock(node_summary: dict, pod_summary: dict, io_summary: dict, alerts: list):
    """Summarize cluster health with Bedrock."""
    alerts_text = "\n".join(
        [f"- {a.get('name')} ({a.get('severity')}): {a.get('summary')}" for a in alerts]
    ) or "none"
    prompt = f"""
    너는 인프라 운영 요약을 작성하는 어시스턴트야.
    아래 클러스터 상태를 2~3문장으로 간결하게 요약해줘.
    이모지는 최소로 사용하고, 중요한 이상 징후를 우선으로.

    [Nodes]
    - Ready: {node_summary.get('ready')}/{node_summary.get('total')}
    - NotReady: {node_summary.get('not_ready')}
    - CPU Usage: {node_summary.get('cpu_usage')}
    - Memory Usage: {node_summary.get('mem_usage')}

    [Pods]
    - Running: {pod_summary.get('running')}
    - Pending: {pod_summary.get('pending')}
    - Error: {pod_summary.get('error')}

    [I/O]
    - Disk Read: {io_summary.get('disk_read')}
    - Disk Write: {io_summary.get('disk_write')}
    - Net RX: {io_summary.get('net_rx')}
    - Net TX: {io_summary.get('net_tx')}

    [Active Alerts]
    {alerts_text}
    """
    try:
        return call_bedrock(prompt).strip()
    except Exception as e:
        logger.error(f"Bedrock summary failed: {e}")
        return "요약 생성에 실패했습니다."

def format_health_message(node_summary: dict, pod_summary: dict, io_summary: dict, alerts: list, summary_text: str = ""):
    """클러스터 건강 상태를 Slack Block Kit 형식으로 포맷"""
    cpu_usage = node_summary.get("cpu_usage")
    mem_usage = node_summary.get("mem_usage")
    cpu_text = f"{cpu_usage:.1f}%" if cpu_usage is not None else "n/a"
    mem_text = f"{mem_usage:.1f}%" if mem_usage is not None else "n/a"
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🩺 클러스터 건강검진"
            }
        }
    ]

    if summary_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*요약:*\n{summary_text}"
            }
        })
        blocks.append({"type": "divider"})

    blocks.extend([
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Nodes:*\n{node_summary['ready']}/{node_summary['total']} Ready"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*NotReady:*\n{node_summary['not_ready']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*CPU Usage:*\n{cpu_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Memory Usage:*\n{mem_text}"
                }
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Pods Running:*\n{pod_summary['running']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Pods Pending:*\n{pod_summary['pending']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Pods Error:*\n{pod_summary['error']}"
                }
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Disk Read:*\n{format_bytes_per_sec(io_summary.get('disk_read'))}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Disk Write:*\n{format_bytes_per_sec(io_summary.get('disk_write'))}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Net RX:*\n{format_bytes_per_sec(io_summary.get('net_rx'))}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Net TX:*\n{format_bytes_per_sec(io_summary.get('net_tx'))}"
                }
            ]
        },
        {"type": "divider"}
    ])

    if not alerts:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ 활성 알람 없음"
            }
        })
        return blocks

    alert_lines = []
    for alert in alerts:
        name = alert.get("name", "unknown")
        severity = alert.get("severity", "n/a")
        summary = alert.get("summary", "")
        line = f"*{name}* ({severity})"
        if summary:
            line += f" - {summary}"
        alert_lines.append(line)

    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*활성 알람:*\n" + "\n".join(alert_lines)
        }
    })
    return blocks

def format_events_message(events: list):
    """최근 이벤트를 Slack Block Kit 형식으로 포맷"""
    if not events:
        return [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": "✅ 현재 보고된 특이 이벤트가 없습니다."}
        }]

    rows = []
    for item in events:
        if hasattr(item, "reason"):
            reason = item.reason or "unknown"
            message = item.message or ""
            involved = item.involved_object
            if involved:
                obj = f"{involved.kind}/{involved.name}" if involved.name else involved.kind
            else:
                obj = "unknown"
            timestamp = item.last_timestamp or item.event_time or item.first_timestamp or "n/a"
        else:
            reason = item.get("reason", "unknown")
            message = item.get("message", "")
            involved = item.get("involvedObject") or item.get("involved_object") or {}
            obj_name = involved.get("name") or "unknown"
            obj_kind = involved.get("kind")
            obj = f"{obj_kind}/{obj_name}" if obj_kind else obj_name
            timestamp = (
                item.get("lastTimestamp")
                or item.get("eventTime")
                or item.get("firstTimestamp")
                or item.get("last_timestamp")
                or item.get("event_time")
                or item.get("first_timestamp")
                or "n/a"
            )
        rows.append({
            "time": str(timestamp),
            "reason": str(reason),
            "target": str(obj),
            "message": str(message).strip()
        })

    header = f"{'TIME':19}  {'REASON':16}  {'TARGET':32}  {'MESSAGE'}"
    sep = "-" * len(header)
    lines = [header, sep]
    for row in rows:
        time_text = row["time"][:19].ljust(19)
        reason_text = row["reason"][:16].ljust(16)
        target_text = row["target"][:32].ljust(32)
        msg = row["message"]
        if msg:
            msg = msg.replace("Successfully pulled image", "Image pulled")
            msg = msg.replace("Pulling image", "Pulling")
            msg = msg.replace("Image size:", "Size:")
            msg = msg.replace("in ", "")
            msg = msg.replace("bytes", "B")
            msg = msg.replace("  ", " ")
        msg_text = msg[:80] if msg else ""
        lines.append(f"{time_text}  {reason_text}  {target_text}  {msg_text}")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🚨 최근 인프라 이벤트 (최근 10건)"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "```\n" + "\n".join(lines) + "\n```"}
        }
    ]

    return blocks

def wrap_with_color(blocks: list, color: str):
    """Wrap blocks in Slack attachment with color bar."""
    return [{
        "color": color,
        "blocks": blocks
    }]

def get_deployment_pods(deployment_name: str):
    """Deployment selector 기반으로 Pod 목록 조회"""
    deployment = k8s_apps_v1.read_namespaced_deployment(
        name=deployment_name,
        namespace=K8S_NAMESPACE
    )
    selector_labels = deployment.spec.selector.match_labels or {}
    if selector_labels:
        label_selector = ",".join([f"{k}={v}" for k, v in selector_labels.items()])
    else:
        label_selector = f"app={deployment_name}"
    pods = k8s_core_v1.list_namespaced_pod(
        namespace=K8S_NAMESPACE,
        label_selector=label_selector
    )
    return deployment, pods.items

def get_recent_pod_log(deployment_name: str, tail_lines: int = 20):
    """Deployment의 최근 Pod 로그 조회"""
    deployment, pods = get_deployment_pods(deployment_name)
    if not pods:
        return {
            "deployment": deployment_name,
            "replicas": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}",
            "status": "No Pods Found",
            "pod_name": None,
            "log": ""
        }
    # 가장 최근에 시작된 Pod 선택
    pods_sorted = sorted(
        pods,
        key=lambda p: p.status.start_time or datetime.min,
        reverse=True
    )
    pod = pods_sorted[0]
    log_text = k8s_core_v1.read_namespaced_pod_log(
        name=pod.metadata.name,
        namespace=K8S_NAMESPACE,
        tail_lines=tail_lines
    )
    return {
        "deployment": deployment_name,
        "replicas": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}",
        "pod_name": pod.metadata.name,
        "log": log_text
    }

@app.get("/health")
def health_check():
    """K8s Liveness Probe용"""
    return {"status": "ok"}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def call_bedrock(prompt):
    """AI 모델 호출 (재시도 로직 포함)"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    # Claude 3.5 Sonnet 모델 ID 사용
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        body=body
    )
    result = json.loads(response.get('body').read())
    return result['content'][0]['text']

def process_alert(data: dict):
    """백그라운드에서 실행될 분석 및 알림 전송 로직"""
    try:
        alerts = data.get("alerts", [])
        if not alerts: return
        update_alert_cache(alerts)

        alert = alerts[0]
        status = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        
        # 해결 메시지는 심플하게 전송
        if status == "resolved":
            send_slack(f"✅ [해결됨] {labels.get('alertname')} 이슈가 정상화되었습니다.")
            return

        # AI 프롬프트 구성 (가독성 & 안전 최우선)
        prompt = f"""
        당신은 AWS EKS 클러스터의 '인프라 모니터링 봇'입니다. 
        엔지니어가 상황을 빠르게 파악할 수 있도록 핵심 정보만 전달하고, 안전한 확인 명령어를 제공하세요.

        [Alert Data]
        - Alert Name: {labels.get('alertname')}
        - Message: {annotations.get('message') or annotations.get('description') or annotations.get('summary')}
        - Labels: {labels}

        [답변 원칙]
        1. 요약 및 원인: 군더더기 없이 핵심만 1~2문장으로 간결하게 작성하세요.
        2. 조치 가이드(중요): 
           - 시스템을 변경하거나 삭제하는 위험한 명령어(delete, scale, reboot 등)는 **절대** 직접 제안하지 마세요.
           - 대신, 상황을 더 자세히 파악할 수 있는 **'조회(Read-only) 명령어'**(`kubectl get`, `describe`, `logs`, `aws ec2 describe-instances` 등)만 제공하세요.
        
        다음 JSON 형식으로 한국어로 답변하세요:
        {{
            "category": "INFRA" 또는 "APP",
            "summary": "핵심 상황 요약 (1문장)",
            "cause": "추정되는 기술적 원인 (2문장 이내)",
            "action": "현황 파악을 위한 조회 명령어 가이드 (안전한 명령어 위주)"
        }}
        """
        
        # AI 분석 실행
        ai_response = call_bedrock(prompt)
        
        try:
            res = json.loads(ai_response)
            
            # 카테고리에 따른 이모지 선택
            icon = "🔧" if res.get('category') == 'INFRA' else "🐛"
            
            msg = (f"🚨 *[{res.get('category', 'ALERT')}] {labels.get('alertname')}*\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"📌 *요약:* {res.get('summary')}\n"
                   f"🔍 *원인:* {res.get('cause')}\n"
                   f"{icon} *조치:* `{res.get('action')}`")
        except:
            msg = f"🚨 *{labels.get('alertname')}*\nAI 분석 내용:\n{ai_response}"

        send_slack(msg)

    except Exception as e:
        logger.error(f"Error: {e}")
        send_slack(f"⚠️ 봇 에러 발생: {str(e)}")

def send_slack(text, channel=None, blocks=None, attachments=None):
    """Slack 메시지 전송 (텍스트 또는 Block Kit 지원)"""
    payload = {
        "channel": channel or SLACK_CHANNEL,
        "text": text
    }
    if blocks:
        payload["blocks"] = blocks
    if attachments:
        payload["attachments"] = attachments
    
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        json=payload
    )
    return response.json()

def get_pod_status(service_name: str, deployment_name: str):
    """특정 서비스의 파드 상태 조회"""
    try:
        # Deployment 정보 조회
        deployment, pods = get_deployment_pods(deployment_name)
        
        if not pods:
            return {
                "service": service_name,
                "deployment": deployment_name,
                "replicas": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}",
                "status": "No Pods Found",
                "details": []
            }
        
        pod_details = []
        for pod in pods:
            container_statuses = pod.status.container_statuses or []
            
            for container in container_statuses:
                # 컨테이너 상태 판단
                if container.state.running:
                    status = "✅ Running"
                elif container.state.waiting:
                    status = f"⏳ Waiting ({container.state.waiting.reason})"
                elif container.state.terminated:
                    status = f"❌ Terminated ({container.state.terminated.reason})"
                else:
                    status = "❓ Unknown"
                
                pod_details.append({
                    "pod_name": pod.metadata.name,
                    "status": status,
                    "restarts": container.restart_count,
                    "image": container.image,
                    "node": pod.spec.node_name
                })
        
        return {
            "service": service_name,
            "deployment": deployment_name,
            "replicas": f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}",
            "details": pod_details
        }
    
    except Exception as e:
        logger.error(f"Error getting pod status for {service_name}: {e}")
        return {
            "service": service_name,
            "status": "Error",
            "error": str(e)
        }

def format_status_message(status_data):
    """상태 정보를 Slack Block Kit 형식으로 포맷"""
    deployment_name = status_data.get("deployment", "unknown")
    replicas = status_data.get("replicas", "0/0")
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 {status_data['service']} 서비스 상태"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Deployment:*\n`{deployment_name}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Replicas:*\n{replicas}"
                }
            ]
        },
        {"type": "divider"}
    ]
    
    # 각 Pod 정보 추가
    for pod in status_data["details"]:
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Pod:*\n`{pod['pod_name']}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{pod['status']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Restarts:*\n{pod['restarts']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Node:*\n`{pod['node']}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Image:*\n`{pod['image']}`"
                }
            ]
        })
        blocks.append({"type": "divider"})
    
    return blocks

def format_logs_message(service_name: str, logs_data: dict):
    """로그 정보를 Slack Block Kit 형식으로 포맷"""
    deployment_name = logs_data.get("deployment", "unknown")
    replicas = logs_data.get("replicas", "0/0")
    pod_name = logs_data.get("pod_name") or "n/a"
    log_text = logs_data.get("log", "").strip()
    if not log_text:
        log_text = "(no logs)"
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📜 {service_name} 로그 (최근 20줄)"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Deployment:*\n`{deployment_name}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Replicas:*\n{replicas}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Pod:*\n`{pod_name}`"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{log_text}```"
            }
        }
    ]
    return blocks

def format_logs_all_message(logs_by_service: list):
    """전체 서비스 로그를 Slack Block Kit 형식으로 포맷"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📜 전체 서비스 로그 (최근 20줄)"}
        }
    ]
    for service_name, logs_data in logs_by_service:
        blocks.append({"type": "divider"})
        blocks.extend(format_logs_message(service_name, logs_data))
    return blocks

def build_service_buttons(action_prefix: str, header_text: str):
    """서비스 선택 버튼 블록 생성"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "조회할 서비스를 선택하세요:"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🧾 All"},
                    "value": "All",
                    "action_id": f"{action_prefix}_all"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔐 Auth"},
                    "value": "Auth",
                    "action_id": f"{action_prefix}_auth"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🤖 AI"},
                    "value": "AI",
                    "action_id": f"{action_prefix}_ai"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📁 Project"},
                    "value": "Project",
                    "action_id": f"{action_prefix}_project"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👥 Team"},
                    "value": "Team",
                    "action_id": f"{action_prefix}_team"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "💬 Support"},
                    "value": "Support",
                    "action_id": f"{action_prefix}_support"
                }
            ]
        }
    ]

def get_pod_identity():
    """Get unique pod identity for lease holding."""
    return os.getenv("POD_NAME") or os.getenv("HOSTNAME") or "infra-bot"

def try_acquire_daily_report_lease(today_str: str):
    """Acquire or renew lease for daily report and check last sent date."""
    holder = get_pod_identity()
    now = datetime.utcnow()
    lease_duration = 600
    annotations = {}
    try:
        lease = k8s_coord.read_namespaced_lease(DAILY_REPORT_LEASE, K8S_NAMESPACE)
        annotations = lease.metadata.annotations or {}
        renew_time = lease.spec.renew_time
        duration = lease.spec.lease_duration_seconds or lease_duration
        expired = True
        if renew_time:
            delta = now - renew_time.replace(tzinfo=None)
            expired = delta.total_seconds() > duration
        if lease.spec.holder_identity == holder or expired:
            lease.spec.holder_identity = holder
            lease.spec.renew_time = now
            lease.spec.lease_duration_seconds = lease_duration
            lease.metadata.annotations = annotations
            k8s_coord.replace_namespaced_lease(DAILY_REPORT_LEASE, K8S_NAMESPACE, lease)
        else:
            return False, annotations
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
        lease_body = client.V1Lease(
            metadata=client.V1ObjectMeta(name=DAILY_REPORT_LEASE, namespace=K8S_NAMESPACE),
            spec=client.V1LeaseSpec(
                holder_identity=holder,
                lease_duration_seconds=lease_duration,
                renew_time=now,
            ),
        )
        k8s_coord.create_namespaced_lease(K8S_NAMESPACE, lease_body)
    return True, annotations

def update_lease_last_sent(window_key: str):
    """Update lease annotation with last sent window."""
    lease = k8s_coord.read_namespaced_lease(DAILY_REPORT_LEASE, K8S_NAMESPACE)
    annotations = lease.metadata.annotations or {}
    annotations["infra-bot/last-sent-window"] = window_key
    lease.metadata.annotations = annotations
    k8s_coord.replace_namespaced_lease(DAILY_REPORT_LEASE, K8S_NAMESPACE, lease)

def send_daily_report():
    """Send daily report to Slack channel."""
    node_summary, pod_summary, io_summary, alerts = build_health_snapshot()
    summary_text = summarize_health_with_bedrock(node_summary, pod_summary, io_summary, alerts)
    blocks = format_health_message(node_summary, pod_summary, io_summary, alerts, summary_text=summary_text)
    color = COLOR_RESOLVED
    if pod_summary.get("error", 0) > 0 or node_summary.get("not_ready", 0) > 0:
        color = COLOR_CRITICAL
    elif pod_summary.get("pending", 0) > 0 or alerts:
        color = COLOR_WARNING
    send_slack("Daily cluster report", blocks=None, channel=None, attachments=wrap_with_color(blocks, color))

def daily_report_loop():
    """Background loop for daily report scheduling."""
    tz = ZoneInfo(DAILY_REPORT_TZ)
    last_local_date = None
    hours = []
    for part in DAILY_REPORT_HOURS.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            hours.append(int(part))
        except ValueError:
            continue
    while True:
        if not DAILY_REPORT_ENABLED:
            time.sleep(60)
            continue
        now = datetime.now(tz)
        today_str = now.strftime("%Y-%m-%d")
        if not hours:
            hours = [9]
        in_window = now.hour in hours and now.minute < DAILY_REPORT_WINDOW_MINUTES
        window_key = f"{today_str}-{now.hour:02d}"
        if in_window and last_local_date != window_key:
            try:
                acquired, annotations = try_acquire_daily_report_lease(today_str)
                last_sent = annotations.get("infra-bot/last-sent-window")
                if acquired and last_sent != window_key:
                    send_daily_report()
                    update_lease_last_sent(window_key)
                last_local_date = window_key
            except Exception as e:
                logger.error(f"Daily report failed: {e}")
        time.sleep(30)

@app.on_event("startup")
def start_daily_report_scheduler():
    """Start daily report scheduler thread."""
    if DAILY_REPORT_ENABLED:
        thread = threading.Thread(target=daily_report_loop, daemon=True)
        thread.start()

@app.post("/slack/commands")
async def slack_command(
    command: str = Form(...),
    text: str = Form(default=""),
    user_id: str = Form(...),
    channel_id: str = Form(...),
    response_url: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """Slack 슬래시 커맨드 처리"""
    logger.info(f"Received command: {command} with text: {text} from user: {user_id}")
    
    if command == "/service-status":
        # 서비스 선택 버튼 표시
        blocks = build_service_buttons("status", "🔍 서비스 상태 조회")
        
        return {
            "response_type": "in_channel",
            "blocks": blocks
        }

    if command == "/logs":
        # 서비스 선택 버튼 표시
        blocks = build_service_buttons("logs", "🧾 서비스 로그 조회")
        return {
            "response_type": "in_channel",
            "blocks": blocks
        }

    if command == "/health":
        if background_tasks is None:
            return {
                "response_type": "in_channel",
                "text": "⚠️ 백그라운드 작업을 사용할 수 없습니다."
            }
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": "🔄 클러스터를 건강검진 중입니다..."
        })
        background_tasks.add_task(process_health_request, response_url)
        return {"status": "received"}

    if command == "/net-check":
        if background_tasks is None:
            return {
                "response_type": "in_channel",
                "text": "⚠️ 백그라운드 작업을 사용할 수 없습니다."
            }
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": "🔄 네트워크 점검을 수행 중입니다..."
        })
        background_tasks.add_task(process_net_check_request, response_url)
        return {"status": "received"}

    if command == "/events":
        try:
            events = k8s_core_v1.list_namespaced_event(
                namespace=K8S_NAMESPACE
            ).items
            events_sorted = sorted(
                events,
                key=lambda e: e.last_timestamp or e.event_time or e.first_timestamp or datetime.min
            )
            items = events_sorted[-10:]
            blocks = format_events_message(items)
            return {
                "response_type": "in_channel",
                "attachments": wrap_with_color(blocks, COLOR_WARNING)
            }
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"❌ 이벤트 조회 중 오류 발생: {str(e)}"
            }
    
    return {"text": "알 수 없는 명령어입니다."}

@app.post("/slack/interactions")
async def slack_interaction(request: Request, background_tasks: BackgroundTasks):
    """Slack 인터랙션 (버튼 클릭 등) 처리"""
    form_data = await request.form()
    payload = json.loads(form_data.get("payload"))
    
    action = payload["actions"][0]
    action_id = action["action_id"]
    service_value = action["value"]
    response_url = payload["response_url"]
    
    logger.info(f"Button clicked: {action_id} for service: {service_value}")
    
    # 즉시 응답 (로딩 메시지)
    if action_id.startswith("status_"):
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": f"🔄 {service_value} 서비스 상태를 조회 중입니다..."
        })
        
        # 백그라운드에서 상태 조회 및 응답
        background_tasks.add_task(process_status_request, service_value, response_url)
    elif action_id.startswith("logs_"):
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": f"🔄 {service_value} 서비스 로그를 조회 중입니다..."
        })
        
        # 백그라운드에서 로그 조회 및 응답
        background_tasks.add_task(process_logs_request, service_value, response_url)
    
    return {"ok": True}

def process_status_request(service_name: str, response_url: str):
    """백그라운드에서 서비스 상태 조회 및 응답"""
    try:
        if service_name == "All":
            blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "📊 전체 서비스 상태"}
                }
            ]
            overall_color = COLOR_RESOLVED
            for svc_name, deployment_name in SERVICES.items():
                status_data = get_pod_status(svc_name, deployment_name)
                if "error" in status_data:
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"❌ *{svc_name}* 상태 조회 실패: {status_data['error']}"}
                    })
                    blocks.append({"type": "divider"})
                    overall_color = COLOR_CRITICAL
                    continue
                if status_data.get("status") == "No Pods Found":
                    overall_color = COLOR_WARNING
                blocks.extend(format_status_message(status_data))
            requests.post(response_url, json={
                "response_type": "in_channel",
                "attachments": wrap_with_color(blocks, overall_color),
                "replace_original": True
            })
            return

        deployment_name = SERVICES.get(service_name)
        if not deployment_name:
            requests.post(response_url, json={
                "response_type": "in_channel",
                "text": f"❌ 알 수 없는 서비스: {service_name}"
            })
            return

        status_data = get_pod_status(service_name, deployment_name)

        if "error" in status_data:
            requests.post(response_url, json={
                "response_type": "in_channel",
                "text": f"❌ 상태 조회 실패: {status_data['error']}"
            })
            return
        color = COLOR_RESOLVED
        if status_data.get("status") == "No Pods Found":
            color = COLOR_WARNING
        blocks = format_status_message(status_data)
        requests.post(response_url, json={
            "response_type": "in_channel",
            "attachments": wrap_with_color(blocks, color),
            "replace_original": True
        })
        
    except Exception as e:
        logger.error(f"Error processing status request: {e}")
        requests.post(response_url, json={
            "response_type": "ephemeral",
            "text": f"❌ 오류 발생: {str(e)}"
        })

def process_logs_request(service_name: str, response_url: str):
    """백그라운드에서 서비스 로그 조회 및 응답"""
    try:
        if service_name == "All":
            logs_by_service = []
            overall_color = COLOR_RESOLVED
            for svc_name, deployment_name in SERVICES.items():
                logs_data = get_recent_pod_log(deployment_name, tail_lines=20)
                if logs_data.get("status") == "No Pods Found":
                    overall_color = COLOR_WARNING
                logs_by_service.append((svc_name, logs_data))
            blocks = format_logs_all_message(logs_by_service)
            requests.post(response_url, json={
                "response_type": "in_channel",
                "attachments": wrap_with_color(blocks, overall_color),
                "replace_original": True
            })
            return

        deployment_name = SERVICES.get(service_name)
        if not deployment_name:
            requests.post(response_url, json={
                "response_type": "in_channel",
                "text": f"❌ 알 수 없는 서비스: {service_name}"
            })
            return
        
        logs_data = get_recent_pod_log(deployment_name, tail_lines=20)
        color = COLOR_RESOLVED
        if logs_data.get("status") == "No Pods Found":
            color = COLOR_WARNING
        blocks = format_logs_message(service_name, logs_data)
        requests.post(response_url, json={
            "response_type": "in_channel",
            "attachments": wrap_with_color(blocks, color),
            "replace_original": True
        })
        
    except Exception as e:
        logger.error(f"Error processing logs request: {e}")
        requests.post(response_url, json={
            "response_type": "ephemeral",
            "text": f"❌ 로그 조회 실패: {str(e)}"
        })

def process_health_request(response_url: str):
    """백그라운드에서 클러스터 건강 상태 조회 및 응답"""
    try:
        node_summary, pod_summary, io_summary, alerts = build_health_snapshot()
        blocks = format_health_message(node_summary, pod_summary, io_summary, alerts)
        color = COLOR_RESOLVED
        if pod_summary.get("error", 0) > 0 or node_summary.get("not_ready", 0) > 0:
            color = COLOR_CRITICAL
        elif pod_summary.get("pending", 0) > 0 or alerts:
            color = COLOR_WARNING
        requests.post(response_url, json={
            "response_type": "in_channel",
            "attachments": wrap_with_color(blocks, color),
            "replace_original": True
        })
    except Exception as e:
        logger.error(f"Error processing health request: {e}")
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": f"❌ 건강검진 조회 실패: {str(e)}"
        })

def process_net_check_request(response_url: str):
    """백그라운드에서 네트워크 점검 및 응답"""
    try:
        ms_results = check_microservices_connectivity()
        aws_results = check_aws_resources()
        blocks = format_net_check_message(ms_results, aws_results)
        color = COLOR_RESOLVED
        if any(r.get("status") == "critical" for r in ms_results + aws_results):
            color = COLOR_CRITICAL
        elif any(r.get("status") == "warning" for r in ms_results + aws_results):
            color = COLOR_WARNING
        requests.post(response_url, json={
            "response_type": "in_channel",
            "attachments": wrap_with_color(blocks, color),
            "replace_original": True
        })
    except Exception as e:
        logger.error(f"Error processing net check: {e}")
        requests.post(response_url, json={
            "response_type": "in_channel",
            "text": f"❌ 네트워크 점검 실패: {str(e)}"
        })

@app.post("/alert")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Grafana Webhook 수신부"""
    data = await request.json()
    # 그라파나의 Timeout 방지를 위해 분석 작업은 백그라운드로 넘기고 즉시 응답
    background_tasks.add_task(process_alert, data)
    return {"status": "received"}
