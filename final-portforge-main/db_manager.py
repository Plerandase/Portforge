#!/usr/bin/env python3
"""
Portforge MSA Database Manager
통합 데이터베이스 관리 스크립트

사용법:
    python db_manager.py reset          # DB 리셋 (데이터 삭제)
    python db_manager.py create         # 테이블 생성
    python db_manager.py seed           # 시드 데이터 삽입
    python db_manager.py reset-seed     # 리셋 + 테이블 생성 + 시드 (전체 초기화)
    python db_manager.py status         # DB 상태 확인
"""
import sys
import os
import subprocess
import argparse
from typing import List, Dict, Tuple

# pymysql 설치 확인 및 자동 설치
try:
    import pymysql
except ImportError:
    print("📦 pymysql 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pymysql", "cryptography", "-q"], check=True)
    import pymysql

# --- 설정 ---
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "rootpassword"
}

DATABASES = [
    "portforge_auth",
    "portforge_project", 
    "portforge_team",
    "portforge_ai",
    "portforge_support"
]

SERVICES = {
    "Auth": "Auth/create_tables.py",
    "Project": "Project_Service/create_tables.py",
    "Team": "Team-BE/create_tables.py",
    "AI": "Ai/create_tables.py",
    "Support": "Support_Communication_Service/create_tables.py"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class DatabaseManager:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0

    def connect_mysql(self) -> pymysql.Connection:
        """MySQL 연결"""
        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.Error as e:
            print(f"MySQL 연결 실패: {e}")
            sys.exit(1)

    def check_db_status(self) -> None:
        """데이터베이스 상태 확인"""
        print("데이터베이스 상태 확인 중...")
        print("-" * 50)
        
        try:
            conn = self.connect_mysql()
            cursor = conn.cursor()
            
            for db in DATABASES:
                cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{db}'")
                exists = cursor.fetchone() is not None
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{db}'")
                    table_count = cursor.fetchone()[0]
                    print(f"  OK {db}: 존재 ({table_count}개 테이블)")
                else:
                    print(f"  NO {db}: 없음")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"상태 확인 실패: {e}")

    def reset_databases(self, confirm: bool = True) -> bool:
        """모든 데이터베이스 리셋"""
        if confirm:
            print("경고: 모든 데이터가 삭제됩니다!")
            print("대상 데이터베이스:")
            for db in DATABASES:
                print(f"  - {db}")
            
            response = input("\n계속하시겠습니까? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("취소되었습니다.")
                return False

        print("\n데이터베이스 리셋 중...")
        
        try:
            conn = self.connect_mysql()
            cursor = conn.cursor()
            
            for db in DATABASES:
                print(f"  {db} 삭제 중...")
                cursor.execute(f"DROP DATABASE IF EXISTS {db}")
                
                print(f"  {db} 생성 중...")
                cursor.execute(f"CREATE DATABASE {db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("데이터베이스 리셋 완료!")
            return True
            
        except Exception as e:
            print(f"리셋 실패: {e}")
            return False

    def create_tables(self) -> bool:
        """모든 서비스의 테이블 생성"""
        print("테이블 생성 중...")
        print("-" * 50)
        
        self.success_count = 0
        self.fail_count = 0
        
        for service_name, script_path in SERVICES.items():
            if self._run_create_tables(service_name, script_path):
                self.success_count += 1
            else:
                self.fail_count += 1
        
        print(f"결과: 성공 {self.success_count}개, 실패 {self.fail_count}개")
        
        if self.fail_count == 0:
            print("모든 테이블 생성 완료!")
            return True
        else:
            print("일부 서비스에서 오류 발생")
            return False

    def _run_create_tables(self, service_name: str, script_path: str) -> bool:
        """개별 서비스 테이블 생성"""
        full_path = os.path.join(BASE_DIR, script_path)
        
        if not os.path.exists(full_path):
            print(f"  WARNING {service_name}: 스크립트 없음 ({script_path})")
            return False
        
        print(f"  {service_name}: 테이블 생성 중...")
        
        try:
            service_dir = os.path.dirname(full_path)
            result = subprocess.run(
                [sys.executable, os.path.basename(full_path)],
                cwd=service_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"  OK {service_name}: 완료")
                return True
            else:
                print(f"  FAIL {service_name}: 실패")
                if result.stderr:
                    print(f"     Error: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT {service_name}: 타임아웃")
            return False
        except Exception as e:
            print(f"  ERROR {service_name}: 예외 - {e}")
            return False

    def seed_data(self) -> bool:
        """시드 데이터 삽입"""
        print("시드 데이터 삽입 중...")
        
        seed_script = os.path.join(BASE_DIR, "seed_all.py")
        if not os.path.exists(seed_script):
            print("seed_all.py 파일을 찾을 수 없습니다.")
            return False
        
        try:
            result = subprocess.run(
                [sys.executable, "seed_all.py"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print("시드 데이터 삽입 완료!")
                return True
            else:
                print("시드 데이터 삽입 실패")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"시드 데이터 삽입 중 오류: {e}")
            return False

    def full_reset(self) -> bool:
        """전체 초기화 (리셋 + 테이블 생성 + 시드)"""
        print("전체 데이터베이스 초기화 시작...")
        print("=" * 60)
        
        # 1. 데이터베이스 리셋
        if not self.reset_databases():
            return False
        
        print()
        
        # 2. 테이블 생성
        if not self.create_tables():
            return False
        
        print()
        
        # 3. 시드 데이터 삽입
        if not self.seed_data():
            return False
        
        print("\n" + "=" * 60)
        print("전체 초기화 완료!")
        print("\n다음 단계:")
        print("  1. DynamoDB 테이블 생성: python create_dynamodb_tables.py")
        print("  2. 서비스 시작: start_services.bat")
        print("  3. 헬스 체크: python test_msa_communication.py")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Portforge MSA Database Manager")
    parser.add_argument("command", choices=["reset", "create", "seed", "reset-seed", "status"],
                       help="실행할 명령")
    parser.add_argument("--no-confirm", action="store_true", 
                       help="확인 없이 실행 (reset 명령용)")
    
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    
    print("Portforge MSA Database Manager")
    print("=" * 60)
    
    if args.command == "status":
        db_manager.check_db_status()
    
    elif args.command == "reset":
        db_manager.reset_databases(confirm=not args.no_confirm)
    
    elif args.command == "create":
        db_manager.create_tables()
    
    elif args.command == "seed":
        db_manager.seed_data()
    
    elif args.command == "reset-seed":
        db_manager.full_reset()
    
    print()


if __name__ == "__main__":
    main()