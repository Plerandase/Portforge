import boto3
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError
from botocore.client import Config
from app.core.config import settings

logger = logging.getLogger(__name__)

class S3Adapter:
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_TEAM
        self.prefix = settings.S3_PREFIX
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # AWS S3 클라이언트 설정
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version='s3v4')
        )

    def _upload_json_sync(self, key: str, data: dict | list):
        try:
            # AI 디렉토리 prefix 추가
            full_key = f"{self.prefix}{key}" if not key.startswith(self.prefix) else key
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=full_key,
                Body=json_str,
                ContentType="application/json"
            )
            logger.info(f"Successfully uploaded to s3://{self.bucket_name}/{full_key}")
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    async def upload_json(self, key: str, data: dict | list):
        """
        Uploads a dictionary or list as a JSON file to S3 (Non-blocking).
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self._upload_json_sync, key, data)

    def _get_json_sync(self, key: str) -> dict | list:
        try:
            full_key = f"{self.prefix}{key}" if not key.startswith(self.prefix) else key
            response = self.client.get_object(Bucket=self.bucket_name, Key=full_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            raise

    async def get_json(self, key: str) -> dict | list:
        """
        Downloads and parses a JSON file from S3 (Non-blocking).
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self.executor, self._get_json_sync, key)
        except Exception as e:
            raise e

s3_adapter = S3Adapter()
