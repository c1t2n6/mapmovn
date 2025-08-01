from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    nickname: str
    dob: datetime
    gender: str  # Nam, Nữ, Khác
    preference: str  # Nam, Nữ, Tất cả
    goal: str  # Mục đích tìm kiếm
    interests: List[str]  # Danh sách sở thích (tối đa 5)

class UserResponse(UserBase):
    id: int
    nickname: Optional[str] = None
    state: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Message schemas
class MessageBase(BaseModel):
    content: str
    message_type: str = "text"

class MessageCreate(MessageBase):
    conversation_id: int

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Conversation schemas
class ConversationBase(BaseModel):
    conversation_type: str = "chat"

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    user1_id: int
    user2_id: int
    user1_keep: bool
    user2_keep: bool
    voice_unlocked: bool
    is_active: bool
    created_at: datetime
    last_activity: datetime
    
    class Config:
        from_attributes = True

# Search schemas
class SearchRequest(BaseModel):
    search_type: str  # "chat" hoặc "voice"

class KeepRequest(BaseModel):
    conversation_id: int
    keep_status: bool

class EndRequest(BaseModel):
    conversation_id: int

# WebSocket schemas
class WebSocketMessage(BaseModel):
    type: str  # "message", "keep", "typing", "end"
    data: dict

class ChatMessage(BaseModel):
    conversation_id: int
    content: str
    message_type: str = "text"

class TypingStatus(BaseModel):
    conversation_id: int
    is_typing: bool

# Response schemas
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None 