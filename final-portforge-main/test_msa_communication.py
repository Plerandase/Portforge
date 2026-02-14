import asyncio
import httpx
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from typing import Dict, List
import os

# --- 환경 설정 ---
os.environ["AWS_ACCESS_KEY_ID"] = "admin"
os.environ["AWS_SECRET_ACCESS_KEY"] = "password123"
os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"

# Boto3 설정 (타임아웃 3초)
my_config = Config(
    connect_timeout=3,
    read_timeout=3,
    retries={'max_attempts': 1}
)

# 서비스 URL 설정
SERVICES = {
    "auth": "http://localhost:8000",
    "project": "http://localhost:8001", 
    "team": "http://localhost:8002",
    "ai": "http://localhost:8003",
    "support": "http://localhost:8004"
}

# 인프라 설정
INFRA = {
    "mysql_host": "localhost",
    "mysql_port": 3306,
    "mysql_user": "root",
    "mysql_password": "rootpassword",
    "s3_endpoint": "http://localhost:9000",
    "ddb_endpoint": "http://localhost:8089",
    "bucket_name": "portforge-team",
    "ddb_tables": ["team_chats", "meeting_sessions"]  # 확인할 테이블 목록
}

async def test_service_health(service_name: str, url: str) -> Dict:
    """개별 서비스 헬스 체크"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{url}/")
            status_code = response.status_code
            status = "🟢 Healthy" if status_code == 200 else f"🟡 Warning ({status_code})"
            
            # API Docs URL 확인 (Swagger UI)
            docs_response = await client.get(f"{url}/docs")
            docs_status = "Available" if docs_response.status_code == 200 else "Unavailable"
            
            return {
                "service": service_name,
                "status": status,
                "docs": docs_status,
                "response_time": response.elapsed.total_seconds(),
            }
    except httpx.ConnectError:
         return {
            "service": service_name,
            "status": "🔴 Connection Refused (Is it running?)",
            "docs": "-",
            "response_time": 0
        }
    except Exception as e:
        return {
            "service": service_name,
            "status": "🔴 Error",
            "error": str(e),
            "response_time": 0
        }

def check_mysql_connection():
    """MySQL 연결 및 데이터베이스 확인"""
    print("  MySQL 연결 확인 중...")  # 진행 상황 출력
    try:
        # pymysql 동적 import
        try:
            import pymysql
        except ImportError:
            return {"name": "MySQL", "status": "🔴 pymysql Not Installed", "detail": "Run: pip install pymysql"}
        
        conn = pymysql.connect(
            host=INFRA['mysql_host'],
            port=INFRA['mysql_port'],
            user=INFRA['mysql_user'],
            password=INFRA['mysql_password'],
            connect_timeout=3
        )
        cursor = conn.cursor()
        
        # 데이터베이스 목록 조회
        cursor.execute("SHOW DATABASES")
        all_dbs = [row[0] for row in cursor.fetchall()]
        
        # Portforge 데이터베이스들 확인
        portforge_dbs = [db for db in all_dbs if db.startswith('portforge_')]
        expected_dbs = ['portforge_auth', 'portforge_project', 'portforge_team', 'portforge_ai', 'portforge_support']
        
        status = "🟢 Connected"
        if len(portforge_dbs) == len(expected_dbs):
            detail = f"All databases present: {portforge_dbs}"
        elif len(portforge_dbs) > 0:
            missing = [db for db in expected_dbs if db not in portforge_dbs]
            status = "🟡 Connected but Missing DBs"
            detail = f"Found: {portforge_dbs}. Missing: {missing}"
        else:
            status = "🟡 Connected (No Portforge DBs)"
            detail = "No portforge databases found"
        
        cursor.close()
        conn.close()
        
        return {"name": "MySQL", "status": status, "detail": detail}
        
    except Exception as e:
        return {"name": "MySQL", "status": "🔴 Connection Failed", "detail": str(e)}

def check_s3_connection():
    """S3 (MinIO) 연결 및 버킷 확인"""
    print("  MinIO 연결 확인 중...")  # 진행 상황 출력
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=INFRA['s3_endpoint'],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_DEFAULT_REGION"],
            config=my_config
        )
        
        # 버킷 목록 조회
        response = s3.list_buckets()
        buckets = [b['Name'] for b in response['Buckets']]
        
        status = "🟢 Connected"
        detail = f"Buckets: {buckets}"
        
        if INFRA['bucket_name'] not in buckets:
            # 버킷이 없으면 생성 시도
            try:
                s3.create_bucket(
                    Bucket=INFRA['bucket_name'],
                    CreateBucketConfiguration={'LocationConstraint': os.environ["AWS_DEFAULT_REGION"]}
                )
                detail += f" -> Created '{INFRA['bucket_name']}'"
            except Exception as e:
                status = "🟡 Connected but Bucket Missing"
                detail += f" -> Failed to create bucket: {e}"
        else:
            detail += f" ('{INFRA['bucket_name']}' exists)"
            
        return {"name": "S3 (MinIO)", "status": status, "detail": detail}
        
    except Exception as e:
        return {"name": "S3 (MinIO)", "status": "🔴 Connection Failed", "detail": str(e)}

def check_dynamodb_connection():
    """DynamoDB Local 연결 및 테이블 확인"""
    print("  DynamoDB 연결 확인 중...") # 진행 상황 출력
    try:
        ddb = boto3.client(
            'dynamodb',
            endpoint_url=INFRA['ddb_endpoint'],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_DEFAULT_REGION"],
            config=my_config
        )
        
        # 테이블 목록 조회
        response = ddb.list_tables()
        tables = response['TableNames']
        
        status = "🟢 Connected"
        
        if tables:
            missing_tables = [t for t in ['team_chats', 'chat_rooms'] if t not in tables]
            if missing_tables:
                status = "🟡 Connected but Tables Missing"
                detail = f"Tables found: {tables}. Missing: {missing_tables}"
            else:
                detail = f"Tables found: {tables} (All tables present)"
        else:
            status = "🟡 Connected (No Tables)"
            detail = "No tables found"
            
        return {"name": "DynamoDB Local", "status": status, "detail": detail}
            
    except Exception as e:
        return {"name": "DynamoDB Local", "status": "🔴 Connection Failed", "detail": str(e)}

async def test_msa_suite():
    """전체 테스트 스위트 실행"""
    print("\n🚀 Portforge MSA Health & Infrastructure Check")
    print("=" * 60)
    
    # 1. 인프라 점검 (동기 실행)
    print("\n🏗️  Infrastructure Check:")
    infra_results = [check_mysql_connection(), check_s3_connection(), check_dynamodb_connection()]
    for res in infra_results:
        print(f"  [{res['name']}]")
        print(f"    Status: {res['status']}")
        print(f"    Detail: {res['detail']}")
    
    # 2. 서비스 헬스 체크 (비동기 병렬 실행)
    print("\n💓 Service Health Check:")
    health_tasks = [test_service_health(name, url) for name, url in SERVICES.items()]
    health_results = await asyncio.gather(*health_tasks)
    
    all_healthy = True
    for result in health_results:
        if "Healthy" not in result['status']:
            all_healthy = False
        
        print(f"  [{result['service'].upper()}] {result['status']}")
        if result.get('response_time', 0) > 0:
            print(f"    Response: {result['response_time']:.3f}s | Docs: {result.get('docs', '-')}")
        if 'error' in result:
             print(f"    Error: {result['error']}")

    print("\n" + "=" * 60)
    
    if all_healthy:
        print("✅ All Systems Operational!")
        print("   You can proceed with frontend integration testing.")
    else:
        print("⚠️  Some services or infrastructure components are not healthy.")
        print("   Run 'poetry run poe db-logs' to see detailed logs.")

if __name__ == "__main__":
    asyncio.run(test_msa_suite())