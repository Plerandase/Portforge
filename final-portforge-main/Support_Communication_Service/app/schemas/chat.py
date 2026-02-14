from pydantic import BaseModel
from typing import Optional

class ChatLogResponse(BaseModel):
    message_id: str
    user_id: str
    message: str
    timestamp: str
    created_at: str

    class Config:
        from_attributes = True

class ChatMessageRequest(BaseModel):
    user_id: str
    message: str
    timestamp: Optional[str] = None