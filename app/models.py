from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import json
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nickname = Column(String)
    dob = Column(DateTime)
    gender = Column(String)  # Nam, Nữ, Khác
    preference = Column(String)  # Nam, Nữ, Tất cả
    goal = Column(String)  # Mục đích tìm kiếm
    interests = Column(Text)  # JSON string của danh sách sở thích
    state = Column(String, default="waiting")  # waiting, searching, connected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships - fixed to avoid ambiguous foreign keys
    conversations_as_user1 = relationship("Conversation", foreign_keys="Conversation.user1_id", back_populates="user1")
    conversations_as_user2 = relationship("Conversation", foreign_keys="Conversation.user2_id", back_populates="user2")
    messages = relationship("Message", back_populates="sender")
    
    def get_interests_list(self):
        """Chuyển đổi interests từ JSON string sang list"""
        if self.interests:
            return json.loads(self.interests)
        return []
    
    def set_interests_list(self, interests_list):
        """Chuyển đổi list interests sang JSON string"""
        self.interests = json.dumps(interests_list)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_type = Column(String, default="chat")  # chat, voice
    user1_keep = Column(Boolean, default=False)
    user2_keep = Column(Boolean, default=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    voice_unlocked = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    countdown_start_time = Column(DateTime(timezone=True), server_default=func.now())  # Thời gian bắt đầu countdown
    
    # Relationships - fixed to avoid ambiguous foreign keys
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="conversations_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="conversations_as_user2")
    messages = relationship("Message", back_populates="conversation")
    
    def get_keep_status(self, user_id):
        """Lấy trạng thái keep của user"""
        if user_id == self.user1_id:
            return self.user1_keep
        elif user_id == self.user2_id:
            return self.user2_keep
        return False
    
    def set_keep_status(self, user_id, status):
        """Set trạng thái keep của user"""
        if user_id == self.user1_id:
            self.user1_keep = status
        elif user_id == self.user2_id:
            self.user2_keep = status
    
    def both_kept(self):
        """Kiểm tra xem cả hai user đã keep chưa"""
        return self.user1_keep and self.user2_keep
    
    def get_countdown_time_left(self):
        """Tính toán thời gian còn lại của countdown (5 phút = 300 giây)"""
        if not self.countdown_start_time:
            return 300  # 5 phút mặc định
        
        # Đảm bảo sử dụng UTC timezone
        if self.countdown_start_time.tzinfo is None:
            # Nếu không có timezone, giả sử là UTC
            start_time = self.countdown_start_time.replace(tzinfo=timezone.utc)
        else:
            start_time = self.countdown_start_time
        
        now = datetime.now(timezone.utc)
        elapsed = (now - start_time).total_seconds()
        time_left = 300 - elapsed  # 300 giây = 5 phút
        
        # Debug log
        print(f"🔍 Countdown calculation for conversation {self.id}:")
        print(f"   Start time: {start_time}")
        print(f"   Now: {now}")
        print(f"   Elapsed: {elapsed:.2f}s")
        print(f"   Time left: {time_left:.2f}s")
        
        return max(0, int(time_left))
    
    def is_countdown_expired(self):
        """Kiểm tra xem countdown đã hết thời gian chưa"""
        return self.get_countdown_time_left() <= 0

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")  # text, image, gif
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", back_populates="messages") 