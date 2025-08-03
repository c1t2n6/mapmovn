from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime, timezone
from app.models import User, Conversation, Message
from sqlalchemy.orm import Session
from collections import defaultdict
import time

class ConnectionManager:
    def __init__(self):
        # Lưu trữ các kết nối WebSocket theo user_id
        self.active_connections: Dict[int, WebSocket] = {}
        # Lưu trữ các kết nối theo conversation_id
        self.conversation_connections: Dict[int, Set[int]] = {}
        # Lưu trữ typing status
        self.typing_status: Dict[int, Dict[int, bool]] = {}  # conversation_id -> {user_id: is_typing}
        # Cache cho conversation info để tránh query database liên tục
        self.conversation_cache: Dict[int, dict] = {}
        # Message queue để batch processing
        self.message_queue: List[dict] = []
        self.processing_queue = False
        # Connection pool cho database
        self.db_pool = []
        self.max_db_connections = 10
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Kết nối WebSocket cho user"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ User {user_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, user_id: int):
        """Ngắt kết nối WebSocket cho user"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"❌ User {user_id} disconnected. Total connections: {len(self.active_connections)}")
        
        # Xóa khỏi tất cả conversation connections
        for conversation_id in list(self.conversation_connections.keys()):
            if user_id in self.conversation_connections[conversation_id]:
                self.conversation_connections[conversation_id].remove(user_id)
                if not self.conversation_connections[conversation_id]:
                    del self.conversation_connections[conversation_id]
                    # Xóa cache khi conversation không còn user nào
                    if conversation_id in self.conversation_cache:
                        del self.conversation_cache[conversation_id]
        
        # Xóa typing status
        for conversation_id in list(self.typing_status.keys()):
            if user_id in self.typing_status[conversation_id]:
                del self.typing_status[conversation_id][user_id]
                if not self.typing_status[conversation_id]:
                    del self.typing_status[conversation_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Gửi tin nhắn cho một user cụ thể với retry logic"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
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
        """Gửi tin nhắn cho tất cả user trong một conversation với parallel processing"""
        if conversation_id in self.conversation_connections:
            users_in_conversation = self.conversation_connections[conversation_id]
            
            # Tạo danh sách user cần gửi tin nhắn
            target_users = [user_id for user_id in users_in_conversation if user_id != exclude_user_id]
            
            if not target_users:
                return
            
            # Gửi tin nhắn song song cho tất cả user
            tasks = [self.send_personal_message(message, user_id) for user_id in target_users]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for result in results if result is True)
            print(f"📤 Message sent to {success_count}/{len(target_users)} users in conversation {conversation_id}")
        else:
            print(f"❌ No users found in conversation {conversation_id}")
    
    def add_to_conversation(self, conversation_id: int, user_id: int):
        """Thêm user vào conversation"""
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(user_id)
        print(f"✅ Added user {user_id} to conversation {conversation_id}. Total users: {len(self.conversation_connections[conversation_id])}")
    
    def remove_from_conversation(self, conversation_id: int, user_id: int):
        """Xóa user khỏi conversation"""
        if conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(user_id)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
                # Xóa cache
                if conversation_id in self.conversation_cache:
                    del self.conversation_cache[conversation_id]
    
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
    
    def get_conversation_info(self, conversation_id: int) -> dict:
        """Lấy thông tin conversation từ cache hoặc database"""
        if conversation_id in self.conversation_cache:
            return self.conversation_cache[conversation_id]
        
        # Nếu không có trong cache, query database
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                info = {
                    'user1_id': conversation.user1_id,
                    'user2_id': conversation.user2_id,
                    'is_active': conversation.is_active,
                    'user1_keep': conversation.user1_keep,
                    'user2_keep': conversation.user2_keep
                }
                # Cache trong 5 phút
                self.conversation_cache[conversation_id] = info
                return info
        finally:
            db.close()
        
        return None
    
    async def process_message_queue(self):
        """Xử lý batch messages từ queue"""
        if self.processing_queue or not self.message_queue:
            return
        
        self.processing_queue = True
        
        try:
            # Lấy tất cả messages trong queue
            messages_to_process = self.message_queue.copy()
            self.message_queue.clear()
            
            if not messages_to_process:
                return
            
            # Group messages theo conversation_id để batch insert
            conversation_messages = defaultdict(list)
            for msg in messages_to_process:
                conversation_messages[msg['conversation_id']].append(msg)
            
            # Process từng conversation
            from app.database import SessionLocal
            db = SessionLocal()
            
            try:
                for conversation_id, messages in conversation_messages.items():
                    # Batch insert messages
                    db_messages = []
                    for msg in messages:
                        db_message = Message(
                            conversation_id=conversation_id,
                            sender_id=msg['sender_id'],
                            content=msg['content'],
                            message_type=msg['message_type']
                        )
                        db_messages.append(db_message)
                    
                    db.add_all(db_messages)
                    
                    # Cập nhật last_activity của conversation
                    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                    if conversation:
                        conversation.last_activity = datetime.now(timezone.utc)
                
                db.commit()
                print(f"✅ Batch processed {len(messages_to_process)} messages")
                
                # Broadcast messages sau khi save thành công
                for msg in messages_to_process:
                    message_to_send = {
                        "type": "chat_message",
                        "data": {
                            "id": msg.get('id'),
                            "conversation_id": msg['conversation_id'],
                            "sender_id": msg['sender_id'],
                            "content": msg['content'],
                            "message_type": msg['message_type'],
                            "created_at": msg['created_at']
                        }
                    }
                    
                    await self.send_to_conversation(message_to_send, msg['conversation_id'], exclude_user_id=msg['sender_id'])
                    
            except Exception as e:
                print(f"❌ Error processing message queue: {e}")
                db.rollback()
            finally:
                db.close()
                
        finally:
            self.processing_queue = False
            # Schedule next processing nếu còn messages
            if self.message_queue:
                asyncio.create_task(self.process_message_queue())

# Global manager instance
manager = ConnectionManager()

class WebSocketHandler:
    def __init__(self):
        self.manager = manager
        self.typing_debounce = {}  # Debounce typing events
    
    async def handle_websocket(self, websocket: WebSocket, user_id: int):
        """Xử lý WebSocket connection cho user"""
        await self.manager.connect(websocket, user_id)
        
        # Tự động thêm user vào conversation nếu họ đang trong một conversation
        await self.auto_add_to_conversation(user_id)
        
        try:
            while True:
                # Nhận tin nhắn từ client với timeout
                try:
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                    message_data = json.loads(data)
                    
                    # Process message async để không block
                    asyncio.create_task(self.process_message(user_id, message_data))
                    
                except asyncio.TimeoutError:
                    # Send ping để keep connection alive
                    try:
                        await websocket.send_text(json.dumps({"type": "ping"}))
                    except:
                        break
                
        except WebSocketDisconnect:
            self.manager.disconnect(user_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.manager.disconnect(user_id)
    
    async def auto_add_to_conversation(self, user_id: int):
        """Tự động thêm user vào conversation nếu họ đang trong một conversation"""
        try:
            # Sử dụng cache trước
            for conversation_id, info in self.manager.conversation_cache.items():
                if info['user1_id'] == user_id or info['user2_id'] == user_id:
                    if info['is_active']:
                        print(f"Auto-adding user {user_id} to conversation {conversation_id} (from cache)")
                        self.manager.add_to_conversation(conversation_id, user_id)
                        return
            
            # Nếu không tìm thấy trong cache, query database
            from app.database import SessionLocal
            db = SessionLocal()
            
            try:
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
        """Xử lý tin nhắn chat với batch processing"""
        conversation_id = data.get("conversation_id")
        content = data.get("content")
        message_type = data.get("message_type", "text")
        
        if not conversation_id or not content:
            print(f"❌ Invalid chat message data from user {user_id}")
            return
        
        print(f"💬 Processing chat message from user {user_id}")
        print(f"   Conversation: {conversation_id}")
        print(f"   Content: {content[:50]}{'...' if len(content) > 50 else ''}")
        
        # Thêm message vào queue để batch processing
        message_data = {
            'conversation_id': conversation_id,
            'sender_id': user_id,
            'content': content,
            'message_type': message_type,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        self.manager.message_queue.append(message_data)
        
        # Trigger batch processing nếu chưa đang xử lý
        if not self.manager.processing_queue:
            asyncio.create_task(self.manager.process_message_queue())
    
    async def handle_typing(self, user_id: int, data: dict):
        """Xử lý trạng thái typing với debouncing"""
        conversation_id = data.get("conversation_id")
        is_typing = data.get("is_typing", False)
        
        if not conversation_id:
            return
        
        # Debounce typing events
        key = f"{conversation_id}_{user_id}"
        
        if key in self.typing_debounce:
            self.typing_debounce[key].cancel()
        
        if is_typing:
            # Broadcast typing status ngay lập tức
            await self.manager.broadcast_typing_status(conversation_id, user_id, True)
            
            # Auto-stop typing sau 2 giây
            task = asyncio.create_task(self.auto_stop_typing(conversation_id, user_id, 2.0))
            self.typing_debounce[key] = task
        else:
            # Stop typing ngay lập tức
            await self.manager.broadcast_typing_status(conversation_id, user_id, False)
    
    async def auto_stop_typing(self, conversation_id: int, user_id: int, delay: float):
        """Tự động dừng typing sau một khoảng thời gian"""
        await asyncio.sleep(delay)
        await self.manager.broadcast_typing_status(conversation_id, user_id, False)
        
        # Xóa task khỏi debounce
        key = f"{conversation_id}_{user_id}"
        if key in self.typing_debounce:
            del self.typing_debounce[key]
    
    async def handle_keep(self, user_id: int, data: dict):
        """Xử lý nút Keep"""
        conversation_id = data.get("conversation_id")
        keep_status = data.get("keep_status", False)
        
        if not conversation_id:
            return
        
        # Sử dụng cache trước
        conversation_info = self.manager.get_conversation_info(conversation_id)
        if not conversation_info:
            return
        
        # Cập nhật database
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conversation:
                conversation.set_keep_status(user_id, keep_status)
                conversation.last_activity = datetime.now(timezone.utc)
                db.commit()
                
                # Cập nhật cache
                if conversation_id in self.manager.conversation_cache:
                    self.manager.conversation_cache[conversation_id].update({
                        'user1_keep': conversation.user1_keep,
                        'user2_keep': conversation.user2_keep
                    })
                
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
        
        # Cập nhật database
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
                        "redirect_to_waiting": True,
                        "redirect_url": "/"
                    }
                }
                
                await self.manager.send_to_conversation(message_to_send, conversation_id)
                
                # Xóa khỏi cache
                if conversation_id in self.manager.conversation_cache:
                    del self.manager.conversation_cache[conversation_id]
                
                # Xóa khỏi conversation connections
                self.manager.remove_from_conversation(conversation_id, user_id)
                
        except Exception as e:
            print(f"❌ Error handling end conversation: {e}")
        finally:
            db.close() 