"""
DynamoDB Adapter for Chat Messages
- 로컬/AWS DynamoDB 모두 지원 (환경변수로 전환)
- 채팅 메시지 저장 및 조회
- 일단위 회의록 관리
"""
import logging
from datetime import datetime, date
from typing import Optional
import json
import aioboto3
from app.core.config import settings

logger = logging.getLogger(__name__)


class DynamoDBAdapter:
    """DynamoDB 어댑터 - 채팅 메시지 및 회의록 관리"""
    
    def __init__(self):
        self.table_name = settings.DDB_TABLE_NAME
        self.endpoint_url = settings.DDB_ENDPOINT_URL or None  # 비어있으면 AWS 사용
        self._session = None
    
    @property
    def session(self):
        if not self._session:
            self._session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return self._session
    
    def _get_client(self):
        """DynamoDB 클라이언트 컨텍스트 매니저 반환"""
        return self.session.client(
            'dynamodb',
            endpoint_url=self.endpoint_url,
            region_name=settings.AWS_REGION
        )
    
    async def ensure_table_exists(self):
        """
        테이블이 없으면 생성 (로컬 개발용)
        AWS에서는 테이블을 미리 생성해두어야 함
        """
        async with self._get_client() as client:
            try:
                await client.describe_table(TableName=self.table_name)
                logger.info(f"Table {self.table_name} already exists")
            except Exception as e:
                if 'ResourceNotFoundException' in str(e):
                    logger.info(f"Creating table {self.table_name}...")
                    await client.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {'AttributeName': 'pk', 'KeyType': 'HASH'},  # team_id#project_id
                            {'AttributeName': 'sk', 'KeyType': 'RANGE'}  # timestamp#msg_id
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'pk', 'AttributeType': 'S'},
                            {'AttributeName': 'sk', 'AttributeType': 'S'},
                            {'AttributeName': 'date_key', 'AttributeType': 'S'},  # GSI용
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'date-index',
                                'KeySchema': [
                                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                                    {'AttributeName': 'date_key', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'},
                                'ProvisionedThroughput': {
                                    'ReadCapacityUnits': 5,
                                    'WriteCapacityUnits': 5
                                }
                            }
                        ],
                        ProvisionedThroughput={
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    )
                    logger.info(f"Table {self.table_name} created successfully")
                else:
                    logger.error(f"Error checking/creating table: {e}")
                    raise
    
    async def save_chat_message(
        self,
        team_id: int,
        project_id: int,
        user: str,
        message: str,
        is_in_meeting: bool = False
    ) -> dict:
        """
        채팅 메시지를 DynamoDB에 저장
        
        Args:
            team_id: 팀 ID
            project_id: 프로젝트 ID
            user: 발신자
            message: 메시지 내용
            is_in_meeting: 회의 중 여부
        
        Returns:
            저장된 메시지 정보
        """
        now = datetime.now()
        timestamp = int(now.timestamp() * 1000)  # 밀리초 단위
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d")
        
        pk = f"TEAM#{team_id}#PROJECT#{project_id}"
        sk = f"MSG#{timestamp}"
        
        item = {
            'pk': {'S': pk},
            'sk': {'S': sk},
            'date_key': {'S': date_str},
            'team_id': {'N': str(team_id)},
            'project_id': {'N': str(project_id)},
            'user': {'S': user},
            'message': {'S': message},
            'time': {'S': time_str},
            'timestamp': {'N': str(timestamp)},
            'is_in_meeting': {'BOOL': is_in_meeting},
            'created_at': {'S': now.isoformat()}
        }
        
        async with self._get_client() as client:
            await client.put_item(
                TableName=self.table_name,
                Item=item
            )
        
        logger.info(f"Chat message saved: {pk}/{sk}")
        
        return {
            'pk': pk,
            'sk': sk,
            'user': user,
            'msg': message,
            'time': time_str,
            'timestamp': timestamp,
            'is_in_meeting': is_in_meeting,
            'date': date_str
        }
    
    async def get_chat_messages(
        self,
        team_id: int,
        project_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        meeting_only: bool = False
    ) -> list[dict]:
        """
        채팅 메시지 조회
        
        Args:
            team_id: 팀 ID
            project_id: 프로젝트 ID
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            meeting_only: 회의 중 메시지만 조회
        
        Returns:
            메시지 목록
        """
        pk = f"TEAM#{team_id}#PROJECT#{project_id}"
        
        async with self._get_client() as client:
            # 기본 쿼리
            params = {
                'TableName': self.table_name,
                'KeyConditionExpression': 'pk = :pk',
                'ExpressionAttributeValues': {
                    ':pk': {'S': pk}
                },
                'ScanIndexForward': True  # 시간순 정렬
            }
            
            # 날짜 필터가 있는 경우 GSI 사용
            if start_date:
                params['IndexName'] = 'date-index'
                params['KeyConditionExpression'] = 'pk = :pk AND date_key >= :start_date'
                params['ExpressionAttributeValues'][':start_date'] = {'S': start_date}
                
                if end_date:
                    params['KeyConditionExpression'] = 'pk = :pk AND date_key BETWEEN :start_date AND :end_date'
                    params['ExpressionAttributeValues'][':end_date'] = {'S': end_date}
            
            # 회의 메시지만 필터
            if meeting_only:
                params['FilterExpression'] = 'is_in_meeting = :meeting'
                params['ExpressionAttributeValues'][':meeting'] = {'BOOL': True}
            
            response = await client.query(**params)
            
            messages = []
            for item in response.get('Items', []):
                messages.append({
                    'user': item['user']['S'],
                    'msg': item['message']['S'],
                    'time': item['time']['S'],
                    'timestamp': int(item['timestamp']['N']),
                    'is_in_meeting': item.get('is_in_meeting', {}).get('BOOL', False),
                    'date': item['date_key']['S']
                })
            
            return messages
    
    async def get_meeting_messages_by_date(
        self,
        team_id: int,
        project_id: int,
        target_date: str
    ) -> list[dict]:
        """
        특정 날짜의 회의 메시지만 조회
        
        Args:
            team_id: 팀 ID
            project_id: 프로젝트 ID
            target_date: 대상 날짜 (YYYY-MM-DD)
        
        Returns:
            해당 날짜의 회의 메시지 목록
        """
        return await self.get_chat_messages(
            team_id=team_id,
            project_id=project_id,
            start_date=target_date,
            end_date=target_date,
            meeting_only=True
        )


# 싱글톤 인스턴스
dynamodb_adapter = DynamoDBAdapter()
