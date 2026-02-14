#!/usr/bin/env python3
"""
Portforge MSA 서비스 시작 스크립트
각 서비스를 지정된 포트에서 실행합니다.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

# 서비스 설정
SERVICES = [
    {
        "name": "Auth Service",
        "path": "Auth",
        "port": 8000,
        "command": "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    },
    {
        "name": "Project Service", 
        "path": "Project_Service",
        "port": 8001,
        "command": "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
    },
    {
        "name": "Team Service",
        "path": "Team-BE", 
        "port": 8002,
        "command": "python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"
    },
    {
        "name": "AI Service",
        "path": "Ai",
        "port": 8003,
        "command": "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload"
    },
    {
        "name": "Support Service",
        "path": "Support_Communication_Service",
        "port": 8004,
        "command": "poetry run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload"
    }
]

def check_port_available(port):
    """포트가 사용 가능한지 확인"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def start_service(service):
    """개별 서비스 시작"""
    print(f"🚀 Starting {service['name']} on port {service['port']}...")
    
    # 포트 확인
    if not check_port_available(service['port']):
        print(f"❌ Port {service['port']} is already in use!")
        return None
    
    # 서비스 디렉토리로 이동하여 실행
    try:
        process = subprocess.Popen(
            service['command'].split(),
            cwd=service['path'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"✅ {service['name']} started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Failed to start {service['name']}: {e}")
        return None

def start_all_services():
    """모든 서비스 시작"""
    print("🏗️ Starting Portforge MSA Services...")
    print("=" * 50)
    
    processes = []
    
    for service in SERVICES:
        process = start_service(service)
        if process:
            processes.append((service, process))
        time.sleep(2)  # 서비스 간 시작 간격
    
    print("\n" + "=" * 50)
    print("📊 Service Status:")
    for service, process in processes:
        status = "🟢 Running" if process.poll() is None else "🔴 Stopped"
        print(f"  {service['name']}: {status} (Port {service['port']})")
    
    print("\n🌐 Service URLs:")
    for service, process in processes:
        if process.poll() is None:
            print(f"  {service['name']}: http://localhost:{service['port']}")
    
    print("\n📚 API Documentation:")
    for service, process in processes:
        if process.poll() is None:
            print(f"  {service['name']}: http://localhost:{service['port']}/docs")
    
    print("\n⚠️  Press Ctrl+C to stop all services")
    
    try:
        # 모든 프로세스가 종료될 때까지 대기
        while any(process.poll() is None for _, process in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
        for service, process in processes:
            if process.poll() is None:
                process.terminate()
                print(f"✅ Stopped {service['name']}")

def start_single_service(service_name):
    """단일 서비스 시작"""
    service = next((s for s in SERVICES if s['name'].lower().replace(' ', '') == service_name.lower().replace(' ', '')), None)
    if not service:
        print(f"❌ Service '{service_name}' not found!")
        print("Available services:")
        for s in SERVICES:
            print(f"  - {s['name']}")
        return
    
    process = start_service(service)
    if process:
        print(f"\n🌐 {service['name']}: http://localhost:{service['port']}")
        print(f"📚 API Docs: http://localhost:{service['port']}/docs")
        print("\n⚠️  Press Ctrl+C to stop the service")
        
        try:
            process.wait()
        except KeyboardInterrupt:
            print(f"\n🛑 Stopping {service['name']}...")
            process.terminate()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        service_name = " ".join(sys.argv[1:])
        start_single_service(service_name)
    else:
        start_all_services()