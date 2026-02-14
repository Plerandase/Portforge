import boto3
import json
import logging
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)

class S3Client:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET_TEAM

    def upload_json(self, data: dict, key: str) -> bool:
        """JSON 데이터를 S3에 업로드"""
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
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except ClientError as e:
            logger.error(f"S3 Download Error: {e}")
            return None

s3_client = S3Client()
