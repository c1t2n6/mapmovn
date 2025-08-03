from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
from datetime import datetime, timezone
from app.models import User, Conversation, Message
from sqlalchemy.orm import Session

class ConnectionManager:
    def __init__(self):
        # Lưu trữ các kết nối WebSocket theo user_id
        self.active_connections: Dict[int, WebSocket] = {}
        # Lưu trữ các kết nối theo conversation_id
        self.conversation_connections: Dict[int, Set[int]] = {}
        # Lưu trữ typing status
        self.typing_status: Dict[int, Dict[int, bool]] = {}  # conversation_id -> {user_id: is_typing}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Kết nối WebSocket cho user"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        """Ngắt kết nối WebSocket cho user"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Xóa khỏi tất cả conversation connections
        for conversation_id in list(self.conversation_connections.keys()):
            if user_id in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(user_id)
                if not self.conversation_connections[conversation_id]:
                    del self.conversation_connections[conversation_id]
        
        # Xóa typing status
        for conversation_id in list(self.typing_status.keys()):
            if user_id in self.typing_status[conversation_id]:
                del self.typing_status[conversation_id][user_id]
                if not self.typing_status[conversation_id]:
                    del self.typing_status[conversation_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Gửi tin nhắn cho một user cụ thể"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
                print(f"✅ Successfully sent message to user {user_id}")
                return True
            except Exception as e:
                print(f"❌ Failed to send message to user {user_id}: {e}")
                # Nếu gửi thất bại, xóa connection
                self.disconnect(user_id)
                return False
        else:
            print(f"⚠️ User {user_id} not connected")
            return False
    
    async def send_to_conversation(self, message: dict, conversation_id: int, exclude_user_id: int = None):
        """Gửi tin nhắn cho tất cả user trong một conversation"""
        if conversation_id in self.conversation_connections:
            users_in_conversation = self.conversation_connections[conversation_id]
            print(f"📤 Sending message to conversation {conversation_id}")
            print(f"   Users in conversation: {users_in_conversation}")
            print(f"   Exclude user: {exclude_user_id}")
            
            success_count = 0
            total_target_users = 0
            
            for user_id in users_in_conversation:
                if user_id != exclude_user_id:
                    total_target_users += 1
                    success = await self.send_personal_message(message, user_id)
                    if success:
                        success_count += 1
            
            print(f"📊 Message delivery result: {success_count}/{total_target_users} users received")
            
            if success_count < total_target_users:
                print(f"⚠️ Some users ({total_target_users - success_count}) did not receive the message")
        else:
            print(f"❌ No users found in conversation {conversation_id}")
            print(f"   Available conversations: {list(self.conversation_connections.keys())}")
    
    def add_to_conversation(self, conversation_id: int, user_id: int):
        """Thêm user vào conversation"""
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(user_id)
        print(f"Added user {user_id} to conversation {conversation_id}. Total users: {self.conversation_connections[conversation_id]}")
    
    def remove_from_conversation(self, conversation_id: int, user_id: int):
        """Xóa user khỏi conversation"""
        if conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(user_id)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
    
    def set_typing_status(self, conversation_id: int, user_id: int, is_typing: bool):
        """Set trạng thái typing của user trong conversation"""
        if conversation_id not in self.typing_status:
            self.typing_status[conversation_id] = {}
        self.typing_status[conversation_id][user_id] = is_typing
    
    def get_typing_status(self, conversation_id: int) -> Dict[int, bool]:
        """Lấy trạng thái typing của tất cả user trong conversation"""
        return self.typing_status.get(conversation_id, {})
    
    async def broadcast_typing_status(self, conversation_id: int, user_id: int, is_typing: bool):
        """Broadcast trạng thái typing cho tất cả user trong conversation"""
        self.set_typing_status(conversation_id, user_id, is_typing)
        
        message = {
            "type": "typing_status",
            "data": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": is_typing
            }
        }
        
        await self.send_to_conversation(message, conversation_id, exclude_user_id=user_id)

# Global instance
manager = ConnectionManager()

class WebSocketHandler:
    def __init__(self):
        self.manager = manager
    
    async def handle_websocket(self, websocket: WebSocket, user_id: int):
        """Xử lý WebSocket connection cho user"""
        await self.manager.connect(websocket, user_id)
        
        # Tự động thêm user vào conversation nếu họ đang trong một conversation
        await self.auto_add_to_conversation(user_id)
        
        try:
            while True:
                # Nhận tin nhắn từ client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                await self.process_message(user_id, message_data)
                
        except WebSocketDisconnect:
            self.manager.disconnect(user_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.manager.disconnect(user_id)
    
    async def auto_add_to_conversation(self, user_id: int):
        """Tự động thêm user vào conversation nếu họ đang trong một conversation"""
        try:
            # Tạo database session mới
            from app.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Tìm conversation active mà user đang tham gia
                conversation = db.query(Conversation).filter(
                    Conversation.is_active == True,
                    ((Conversation.user1_id == user_id) | (Conversation.user2_id == user_id))
                ).first()
                
                if conversation:
                    print(f"Auto-adding user {user_id} to conversation {conversation.id}")
                    self.manager.add_to_conversation(conversation.id, user_id)
                else:
                    print(f"User {user_id} is not in any active conversation")
                    
            finally:
                db.close()
                
        except Exception as e:
            print(f"Error auto-adding user to conversation: {e}")
    
    async def process_message(self, user_id: int, message_data: dict):
        """Xử lý tin nhắn từ WebSocket"""
        message_type = message_data.get("type")
        
        if message_type == "chat_message":
            await self.handle_chat_message(user_id, message_data["data"])
        elif message_type == "typing":
            await self.handle_typing(user_id, message_data["data"])
        elif message_type == "keep":
            await self.handle_keep(user_id, message_data["data"])
        elif message_type == "end_conversation":
            await self.handle_end_conversation(user_id, message_data["data"])
    
    async def handle_chat_message(self, user_id: int, data: dict):
        """Xử lý tin nhắn chat"""
        conversation_id = data.get("conversation_id")
        content = data.get("content")
        message_type = data.get("message_type", "text")
        
        if not conversation_id or not content:
            print(f"❌ Invalid chat message data from user {user_id}")
            return
        
        print(f"💬 Processing chat message from user {user_id}")
        print(f"   Conversation: {conversation_id}")
        print(f"   Content: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        # Tạo database session mới
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            # Lưu tin nhắn vào database
            message = Message(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=content,
                message_type=message_type
            )
            
            db.add(message)
            
            # Cập nhật last_activity của conversation
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.last_activity = datetime.now(timezone.utc)
            
            db.commit()
            print(f"💾 Message saved to database with ID: {message.id}")
            
            # Gửi tin nhắn cho user khác trong conversation
            message_to_send = {
                "type": "chat_message",
                "data": {
                    "id": message.id,
                    "conversation_id": conversation_id,
                    "sender_id": user_id,
                    "content": content,
                    "message_type": message_type,
                    "created_at": message.created_at.isoformat()
                }
            }
            
            print(f"📤 Broadcasting message to conversation {conversation_id}")
            
            # Đảm bảo user được thêm vào conversation trước khi gửi tin nhắn
            if conversation_id not in self.manager.conversation_connections:
                print(f"⚠️ Conversation {conversation_id} not in connections, adding users...")
                # Thêm cả 2 user vào conversation
                if conversation:
                    self.manager.add_to_conversation(conversation_id, conversation.user1_id)
                    self.manager.add_to_conversation(conversation_id, conversation.user2_id)
                    print(f"✅ Added users {conversation.user1_id} and {conversation.user2_id} to conversation {conversation_id}")
            
            await self.manager.send_to_conversation(message_to_send, conversation_id, exclude_user_id=user_id)
            
        except Exception as e:
            print(f"❌ Error handling chat message: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def handle_typing(self, user_id: int, data: dict):
        """Xử lý trạng thái typing"""
        conversation_id = data.get("conversation_id")
        is_typing = data.get("is_typing", False)
        
        if conversation_id:
            await self.manager.broadcast_typing_status(conversation_id, user_id, is_typing)
    
    async def handle_keep(self, user_id: int, data: dict):
        """Xử lý nút Keep"""
        conversation_id = data.get("conversation_id")
        keep_status = data.get("keep_status", False)
        
        if not conversation_id:
            return
        
        # Tạo database session mới
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.set_keep_status(user_id, keep_status)
                conversation.last_activity = datetime.now(timezone.utc)
                db.commit()
                
                # Gửi thông báo keep cho user khác
                message_to_send = {
                    "type": "keep_status",
                    "data": {
                        "conversation_id": conversation_id,
                        "user_id": user_id,
                        "keep_status": keep_status,
                        "both_kept": conversation.both_kept()
                    }
                }
                
                await self.manager.send_to_conversation(message_to_send, conversation_id, exclude_user_id=user_id)
        except Exception as e:
            print(f"❌ Error handling keep: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def handle_end_conversation(self, user_id: int, data: dict):
        """Xử lý kết thúc conversation"""
        conversation_id = data.get("conversation_id")
        
        if not conversation_id:
            return
        
        # Tạo database session mới
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                # Gửi thông báo kết thúc cho tất cả user trong conversation
                message_to_send = {
                    "type": "conversation_ended",
                    "data": {
                        "conversation_id": conversation_id,
                        "ended_by": user_id,
                        "redirect_to_waiting": True
                    }
                }
                
                await self.manager.send_to_conversation(message_to_send, conversation_id)
                
                # Xóa tất cả user khỏi conversation connections
                self.manager.remove_from_conversation(conversation_id, user_id)
        except Exception as e:
            print(f"❌ Error handling end conversation: {e}")
        finally:
            db.close() 