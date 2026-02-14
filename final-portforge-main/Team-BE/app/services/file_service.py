"""
파일 업로드/다운로드 서비스 (AWS S3)
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.access_key = settings.AWS_ACCESS_KEY_ID
        self.secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.bucket_name = settings.S3_BUCKET_TEAM
        self.region = settings.AWS_REGION
        
        # AWS S3 클라이언트 초기화
        self.client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        
        logger.info(f"FileService 초기화: bucket={self.bucket_name}, region={self.region}")
    
    def upload_file(self, file: UploadFile, team_id: int, user_id: str) -> dict:
        """
        파일 업로드
        
        Args:
            file: 업로드할 파일
            team_id: 팀 ID
            user_id: 업로드한 사용자 ID
            
        Returns:
            dict: 업로드된 파일 정보
        """
        try:
            # 파일 크기 체크 (10MB)
            MAX_FILE_SIZE = 10 * 1024 * 1024
            
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="파일 크기가 10MB를 초과합니다."
                )
            
            # 파일명 생성
            file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # S3 키 생성: {team_id}/shared/{unique_filename}
            s3_key = f"{team_id}/shared/{unique_filename}"
            
            # S3에 파일 업로드
            self.client.upload_fileobj(
                file.file,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
            )
            
            logger.info(f"파일 업로드 성공: {s3_key}")
            
            return {
                "s3_key": s3_key,
                "original_filename": file.filename,
                "file_size": file_size,
                "content_type": file.content_type,
                "uploaded_by": user_id,
                "uploaded_at": datetime.now()
            }
            
        except ClientError as e:
            logger.error(f"S3 업로드 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="파일 업로드에 실패했습니다."
            )
        except Exception as e:
            logger.error(f"파일 업로드 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
            )
    
    def get_download_url(self, s3_key: str, expires: int = 3600) -> str:
        """
        파일 다운로드 URL 생성 (Presigned URL)
        
        Args:
            s3_key: S3 객체 키
            expires: URL 만료 시간 (초, 기본 1시간)
            
        Returns:
            str: 다운로드 URL
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires
            )
            return url
        except ClientError as e:
            logger.error(f"다운로드 URL 생성 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail="다운로드 URL 생성에 실패했습니다."
            )
    
    def get_file_stream(self, s3_key: str):
        """
        Return streaming body and content metadata for download.
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=s3_key)
            body = response["Body"]
            content_type = response.get("ContentType") or "application/octet-stream"
            content_length = response.get("ContentLength")
            return body, content_type, content_length
        except ClientError as e:
            logger.error(f"Failed to stream file from S3: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to read file from storage."
            )

    def delete_file(self, s3_key: str) -> bool:
        """
        파일 삭제
        
        Args:
            s3_key: 삭제할 파일의 S3 키
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"파일 삭제 성공: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"파일 삭제 실패: {e}")
            return False
    
    def get_file_info(self, s3_key: str) -> Optional[dict]:
        """
        파일 정보 조회
        
        Args:
            s3_key: S3 객체 키
            
        Returns:
            dict: 파일 정보 또는 None
        """
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                "size": response['ContentLength'],
                "content_type": response['ContentType'],
                "last_modified": response['LastModified'],
                "etag": response['ETag']
            }
        except ClientError as e:
            logger.error(f"파일 정보 조회 실패: {e}")
            return None
    
    def list_team_files(self, team_id: int) -> List[dict]:
        """
        팀의 공유 파일 목록 조회
        
        Args:
            team_id: 팀 ID
            
        Returns:
            List[dict]: 파일 목록
        """
        try:
            prefix = f"teams/{team_id}/shared/"
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "s3_key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified']
                })
            return files
        except ClientError as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            return []

# 전역 파일 서비스 인스턴스
file_service = FileService()
