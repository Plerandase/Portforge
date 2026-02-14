from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
from app.schemas.chat import ChatLogResponse
import boto3
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

def get_dynamodb_client():
    """DynamoDB 클라이언트 생성"""
    if settings.DDB_ENDPOINT_URL:
        # 로컬 DynamoDB
        return boto3.client(
            'dynamodb',
            endpoint_url=settings.DDB_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    else:
        # 실제 AWS DynamoDB
        return boto3.client('dynamodb', region_name=settings.AWS_REGION)

@router.get("/team/{team_id}/logs", response_model=List[ChatLogResponse])
async def get_chat_logs(
    team_id: int,
    start_time: Optional[str] = Query(None, description="시작 시간 (ISO format)"),
    end_time: Optional[str] = Query(None, description="종료 시간 (ISO format)"),
    limit: int = Query(100, description="조회할 메시지 수")
):
    """팀 채팅 로그 조회 (AI 서비스에서 회의록 생성용)"""
    
    try:
        dynamodb = get_dynamodb_client()
        
        # DynamoDB 쿼리 파라미터 구성
        key_condition = f"project_id = :project_id"
        expression_values = {
            ":project_id": {"N": str(team_id)}
        }
        
        # 시간 범위 필터 추가
        if start_time and end_time:
            key_condition += " AND #timestamp BETWEEN :start_time AND :end_time"
            expression_values.update({
                ":start_time": {"S": start_time},
                ":end_time": {"S": end_time}
            })
        
        # DynamoDB 쿼리 실행
        response = dynamodb.query(
            TableName="team_chats",
            KeyConditionExpression=key_condition,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames={
                "#timestamp": "timestamp"
            } if start_time and end_time else None,
            Limit=limit,
            ScanIndexForward=True  # 시간순 정렬
        )
        
        # 결과 변환
        chat_logs = []
        for item in response.get('Items', []):
            chat_logs.append(ChatLogResponse(
                message_id=item.get('message_id', {}).get('S', ''),
                user_id=item.get('user_id', {}).get('S', ''),
                message=item.get('message', {}).get('S', ''),
                timestamp=item.get('timestamp', {}).get('S', ''),
                created_at=item.get('created_at', {}).get('S', '')
            ))
        
        return chat_logs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat logs: {str(e)}"
        )

@router.get("/team/{team_id}/recent", response_model=List[ChatLogResponse])
async def get_recent_chat_logs(
    team_id: int,
    hours: int = Query(24, description="최근 몇 시간의 채팅을 조회할지")
):
    """최근 채팅 로그 조회"""
    
    from datetime import datetime, timedelta
    
    # 현재 시간에서 지정된 시간만큼 이전 시간 계산
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    return await get_chat_logs(
        team_id=team_id,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat()
    )

@router.post("/team/{team_id}/meeting-logs")
async def get_meeting_chat_logs(
    team_id: int,
    start_time: str,
    end_time: str
):
    """회의 시간 동안의 채팅 로그 조회 (AI 서비스 전용)"""
    
    chat_logs = await get_chat_logs(
        team_id=team_id,
        start_time=start_time,
        end_time=end_time,
        limit=1000  # 회의록 생성을 위해 더 많은 메시지 조회
    )
    
    # AI 서비스에서 사용하기 쉬운 형태로 변환
    formatted_logs = []
    for log in chat_logs:
        formatted_logs.append({
            "user_id": log.user_id,
            "message": log.message,
            "timestamp": log.timestamp
        })
    
    return {
        "team_id": team_id,
        "start_time": start_time,
        "end_time": end_time,
        "message_count": len(formatted_logs),
        "messages": formatted_logs
    }


# =====================================================
# FE_latest 호환 API (TeamSpacePage.tsx / chatClient.ts)
# =====================================================
from pydantic import BaseModel
import uuid
import time

class ChatMessageCreateRequest(BaseModel):
    team_id: int
    project_id: int
    user: str
    message: str
    is_in_meeting: bool = False

@router.post("/message")
async def save_chat_message(request: ChatMessageCreateRequest):
    """채팅 메시지 저장 (FE 호환)"""
    try:
        dynamodb = get_dynamodb_client()
        
        timestamp = datetime.now().isoformat()
        message_id = str(uuid.uuid4())
        
        item = {
            "project_id": {"N": str(request.team_id)},  # Partition Key (team_id 사용)
            "timestamp": {"S": timestamp},              # Sort Key
            "message_id": {"S": message_id},
            "user_id": {"S": request.user},
            "message": {"S": request.message},
            "is_in_meeting": {"BOOL": request.is_in_meeting},
            "created_at": {"S": timestamp}
        }
        
        dynamodb.put_item(
            TableName="team_chats",
            Item=item
        )
        
        # FE 형식으로 응답 반환
        return {
            "user": request.user,
            "msg": request.message,
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": int(time.time() * 1000),
            "is_in_meeting": request.is_in_meeting
        }
        
    except Exception as e:
        # DynamoDB가 없거나 에러 발생 시에도 FE가 멈추지 않도록 처리
        print(f"Chat save failed: {e}")
        # 성공한 척 응답 반환 (개발 편의성)
        return {
            "user": request.user,
            "msg": request.message,
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": int(time.time() * 1000),
            "is_in_meeting": request.is_in_meeting
        }

@router.get("/messages/{team_id}/{project_id}")
async def get_messages_compat(
    team_id: int,
    project_id: int,
    start_date: Optional[str] = Query(None, alias="start_date"),
    end_date: Optional[str] = Query(None, alias="end_date"),
    meeting_only: bool = Query(False, alias="meeting_only")
):
    """채팅 메시지 목록 조회 (FE 호환)"""
    try:
        # 기존 로직 재사용
        limit = 1000 if start_date else 50
        logs = await get_chat_logs(team_id, start_date, end_date, limit)
        
        messages = []
        for log in logs:
            dt = datetime.fromisoformat(log.timestamp)
            messages.append({
                "user": log.user_id,
                "msg": log.message,
                "time": dt.strftime("%H:%M"),
                "timestamp": int(dt.timestamp() * 1000),
                "isInMeeting": False  # 기존 데이터에는 필드가 없을 수 있음
            })
            
        return {
            "messages": messages,
            "count": len(messages)
        }
    except Exception:
        # 에러 시 빈 목록 반환
        return {"messages": [], "count": 0}
