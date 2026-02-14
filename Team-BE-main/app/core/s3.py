import boto3
import json
import logging
from botocore.exceptions import ClientError
from app.core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

class S3Client:
    def __init__(self):
        try:
            self.s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket = settings.S3_BUCKET_TEAM
            self.is_ready = True
        except Exception as e:
            logger.error(f"Failed to initialize S3 Client: {e}")
            self.s3 = None
            self.bucket = None
            self.is_ready = False

    def upload_json(self, data: dict, key: str) -> bool:
        """JSON 데이터를 S3에 업로드"""
        if not self.is_ready:
            logger.warning("S3 Client is not ready. Skipping upload.")
            return False
            
        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False),
                ContentType="application/json"
            )
            return True
        except ClientError as e:
            logger.error(f"S3 Upload Error: {e}")
            return False

    def get_json(self, key: str) -> dict:
        """S3에서 JSON 데이터 다운로드"""
        if not self.is_ready:
            return None

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            logger.error(f"S3 Download Error: {e}")
            return None

    def delete_object(self, key: str) -> bool:
        """S3에서 객체 삭제"""
        if not self.is_ready:
            logger.warning("S3 Client is not ready. Skipping delete.")
            return False
            
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"S3 객체 삭제 성공: {key}")
            return True
        except ClientError as e:
            logger.error(f"S3 Delete Error: {e}")
            return False

s3_client = S3Client()
