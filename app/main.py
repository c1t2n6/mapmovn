from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import os
import asyncio
import random
import json
from datetime import datetime, timedelta

from app.database import engine, get_db
from app.models import Base, User, Conversation, Message
from app.schemas import (
    UserCreate, UserLogin, UserProfile, UserResponse,
    MessageCreate, MessageResponse, ConversationResponse,
    SearchRequest, KeepRequest, EndRequest, SuccessResponse, ErrorResponse
)
from app.auth import hash_password, verify_password, create_access_token, get_current_user, authenticate_user
from app.matching import MatchingService
from app.websocket_manager import WebSocketHandler, manager

# Tạo database tables
Base.metadata.create_all(bind=engine)

def create_default_users():
    """Tạo 3 tài khoản mặc định: user1, user2, user3 với mật khẩu 'password'"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Danh sách tên ngẫu nhiên
        random_names = [
            "An", "Bình", "Cường", "Dung", "Em", "Phương", "Giang", "Hoa", "Iris", "Jade",
            "Khang", "Linh", "Minh", "Nga", "Oanh", "Phúc", "Quỳnh", "Rosa", "Sơn", "Thảo",
            "Uyên", "Vân", "Xuân", "Yến", "Zoe", "Alpha", "Beta", "Charlie", "Delta", "Echo"
        ]
        
        # Danh sách sở thích ngẫu nhiên
        random_interests_lists = [
            ["Tập gym 💪", "Chụp ảnh 📷", "Du lịch ✈️"],
            ["Nhảy nhót 💃", "Uống cà phê ☕", "Đọc sách 📚"],
            ["Chơi game 🎮", "Nghe nhạc 🎧", "Xem phim 🍿"],
            ["Leo núi 🏔️", "Nghệ thuật 🎨", "Ăn ngon 🥘"],
            ["Làm tình nguyện ❤️", "Tâm linh ✨", "Thời trang 👗"],
            ["Tập gym 💪", "Du lịch ✈️", "Nghe nhạc 🎧"],
            ["Chụp ảnh 📷", "Uống cà phê ☕", "Xem phim 🍿"],
            ["Nhảy nhót 💃", "Đọc sách 📚", "Ăn ngon 🥘"]
        ]
        
        # Danh sách mục tiêu ngẫu nhiên
        random_goals = [
            "Một mối quan hệ nhẹ nhàng, vui vẻ",
            "Một mối quan hệ nghiêm túc",
            "Chưa chắc, muốn khám phá thêm",
            "Kết hôn",
            "Bạn đời lâu dài",
            "Mối quan hệ mở",
            "Kết bạn mới thôi 🥰"
        ]
        
        # Danh sách giới tính và sở thích
        genders = ["Nam", "Nữ", "Khác"]
        preferences = ["Nam", "Nữ", "Tất cả"]
        
        # Tạo 3 user mặc định
        default_users = ["user1", "user2", "user3"]
        
        for i, username in enumerate(default_users):
            # Kiểm tra xem user đã tồn tại chưa
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                print(f"✅ User {username} đã tồn tại, bỏ qua")
                continue
            
            # Tạo thông tin ngẫu nhiên
            nickname = random.choice(random_names)
            gender = random.choice(genders)
            preference = random.choice(preferences)
            goal = random.choice(random_goals)
            interests = random.choice(random_interests_lists)
            
            # Tạo ngày sinh ngẫu nhiên (18-35 tuổi)
            current_year = datetime.now().year
            birth_year = random.randint(current_year - 35, current_year - 18)
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)  # Sử dụng 28 để tránh lỗi tháng 2
            dob = datetime(birth_year, birth_month, birth_day)
            
            # Tạo user mới
            hashed_password = hash_password("password")
            new_user = User(
                username=username,
                password_hash=hashed_password,
                nickname=nickname,
                dob=dob,
                gender=gender,
                preference=preference,
                goal=goal,
                interests=json.dumps(interests),
                state="waiting"
            )
            
            db.add(new_user)
            print(f"✅ Đã tạo user {username} với nickname: {nickname}")
        
        db.commit()
        print("🎉 Hoàn thành tạo 3 tài khoản mặc định!")
        
    except Exception as e:
        print(f"❌ Lỗi khi tạo default users: {e}")
        db.rollback()
    finally:
        db.close()

app = FastAPI(title="Mapmo.vn - Anonymous Web Chat", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production, chỉ cho phép domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Constants
INTERESTS_OPTIONS = [
    "Tập gym 💪", "Nhảy nhót 💃", "Chụp ảnh 📷", "Uống cà phê ☕", "Du lịch ✈️",
    "Chơi game 🎮", "Đọc sách 📚", "Nghe nhạc 🎧", "Làm tình nguyện ❤️", "Xem phim 🍿",
    "Leo núi 🏔️", "Nghệ thuật 🎨", "Ăn ngon 🥘", "Tâm linh ✨", "Thời trang 👗"
]

GOAL_OPTIONS = [
    "Một mối quan hệ nhẹ nhàng, vui vẻ",
    "Một mối quan hệ nghiêm túc",
    "Chưa chắc, muốn khám phá thêm",
    "Kết hôn",
    "Bạn đời lâu dài",
    "Mối quan hệ mở",
    "Kết bạn mới thôi 🥰"
]

# Background task để tự động xóa conversation hết countdown
async def cleanup_expired_conversations():
    """Background task để dọn dẹp các conversation hết hạn"""
    while True:
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Lấy tất cả conversation active
                active_conversations = db.query(Conversation).filter(
                    Conversation.is_active == True
                ).all()
                
                for conversation in active_conversations:
                    # Kiểm tra xem countdown đã hết thời gian chưa
                    if conversation.is_countdown_expired() and not conversation.both_kept():
                        print(f"⏰ Conversation {conversation.id} expired, ending...")
                        
                        # Broadcast countdown update trước khi kết thúc
                        await manager.broadcast_countdown_update(conversation.id)
                        
                        # Kết thúc conversation
                        conversation.is_active = False
                        
                        # Cập nhật trạng thái user về waiting
                        user1 = db.query(User).filter(User.id == conversation.user1_id).first()
                        user2 = db.query(User).filter(User.id == conversation.user2_id).first()
                        
                        if user1:
                            user1.state = "waiting"
                        if user2:
                            user2.state = "waiting"
                        
                        # Gửi thông báo kết thúc cho cả 2 user
                        end_message = {
                            "type": "conversation_ended",
                            "data": {
                                "conversation_id": conversation.id,
                                "reason": "countdown_expired",
                                "redirect_url": "/"
                            }
                        }
                        
                        await manager.send_to_conversation(end_message, conversation.id)
                        
                        print(f"✅ Conversation {conversation.id} ended due to countdown expiration")
                
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error in cleanup_expired_conversations: {e}")
        
        # Chạy mỗi 30 giây
        await asyncio.sleep(30)

async def broadcast_countdown_updates():
    """Background task để broadcast countdown updates cho tất cả conversation active"""
    while True:
        try:
            from app.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Lấy tất cả conversation active
                active_conversations = db.query(Conversation).filter(
                    Conversation.is_active == True
                ).all()
                
                for conversation in active_conversations:
                    # Chỉ broadcast nếu có user đang kết nối
                    if conversation.id in manager.conversation_connections:
                        await manager.broadcast_countdown_update(conversation.id)
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error in broadcast_countdown_updates: {e}")
        
        # Broadcast mỗi 10 giây
        await asyncio.sleep(10)

# Startup event để bắt đầu background task
@app.on_event("startup")
async def startup_event():
    """Khởi động background task khi app start"""
    print("🚀 Khởi động server...")
    
    # Tạo 3 tài khoản mặc định
    create_default_users()
    
    # Bắt đầu background task
    asyncio.create_task(cleanup_expired_conversations())
    asyncio.create_task(broadcast_countdown_updates())
    
    print("✅ Server đã sẵn sàng!")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Trang chủ - redirect đến login"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/chat/{conversation_id}", response_class=HTMLResponse)
async def chat_room(conversation_id: int):
    """Endpoint để vào phòng chat cụ thể"""
    # Trả về trang HTML cơ bản, JavaScript sẽ xử lý xác thực và load conversation
    with open("static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Thêm script để tự động load conversation khi user đã đăng nhập
    script = f"""
    <script>
        // Tự động load conversation khi vào URL
        window.addEventListener('load', function() {{
            if (window.app) {{
                window.app.loadConversationFromUrl({conversation_id});
            }} else {{
                // Nếu app chưa được khởi tạo, đợi một chút
                setTimeout(function() {{
                    if (window.app) {{
                        window.app.loadConversationFromUrl({conversation_id});
                    }}
                }}, 100);
            }}
        }});
    </script>
    """
    
    # Chèn script vào cuối body
    html_content = html_content.replace('</body>', f'{script}</body>')
    
    return HTMLResponse(content=html_content)

@app.get("/api/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại"""
    return UserResponse.from_orm(current_user)

@app.post("/register", response_model=SuccessResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản mới"""
    # Kiểm tra password xác nhận
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp"
        )
    
    # Kiểm tra username đã tồn tại chưa
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại"
        )
    
    # Tạo user mới
    hashed_password = hash_password(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        state="waiting"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return SuccessResponse(
        success=True,
        message="Đăng ký thành công",
        data={"user_id": new_user.id}
    )

@app.post("/login", response_model=SuccessResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Đăng nhập"""
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng"
        )
    
    # Tạo access token
    access_token = create_access_token(data={"sub": user.username})
    
    return SuccessResponse(
        success=True,
        message="Đăng nhập thành công",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "state": user.state,
                "profile_completed": user.nickname is not None
            }
        }
    )

@app.post("/logout", response_model=SuccessResponse)
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Đăng xuất"""
    # Cập nhật trạng thái user về waiting
    current_user.state = "waiting"
    db.commit()
    
    return SuccessResponse(
        success=True,
        message="Đăng xuất thành công"
    )

@app.put("/profile", response_model=SuccessResponse)
async def update_profile(
    profile_data: UserProfile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật hồ sơ người dùng"""
    # Kiểm tra số lượng sở thích
    if len(profile_data.interests) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ được chọn tối đa 5 sở thích"
        )
    
    # Cập nhật thông tin
    current_user.nickname = profile_data.nickname
    current_user.dob = profile_data.dob
    current_user.gender = profile_data.gender
    current_user.preference = profile_data.preference
    current_user.goal = profile_data.goal
    current_user.set_interests_list(profile_data.interests)
    
    db.commit()
    
    return SuccessResponse(
        success=True,
        message="Cập nhật hồ sơ thành công"
    )

@app.get("/profile/options", response_model=dict)
async def get_profile_options():
    """Lấy danh sách các tùy chọn cho hồ sơ"""
    return {
        "interests": INTERESTS_OPTIONS,
        "goals": GOAL_OPTIONS
    }

@app.post("/search", response_model=SuccessResponse)
async def start_search(
    search_data: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bắt đầu tìm kiếm chat hoặc voice call"""
    try:
        # Kiểm tra user đã hoàn thành hồ sơ chưa
        if not current_user.nickname:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng hoàn thành hồ sơ trước khi tìm kiếm"
            )
        
        # Kiểm tra xem user đã có conversation active chưa
        existing_conversation = db.query(Conversation).filter(
            ((Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)) &
            (Conversation.is_active == True)
        ).first()
        
        if existing_conversation:
            # User đã có conversation active, trả về thông tin conversation
            other_user_id = existing_conversation.user2_id if existing_conversation.user1_id == current_user.id else existing_conversation.user1_id
            other_user = db.query(User).filter(User.id == other_user_id).first()
            
            # Đảm bảo user hiện tại có trạng thái "connected"
            if current_user.state != "connected":
                current_user.state = "connected"
                db.commit()
                print(f"🔄 Updated user {current_user.id} state from {current_user.state} to connected")
            
            # Thêm vào WebSocket connections nếu chưa có
            manager.add_to_conversation(existing_conversation.id, current_user.id)
            
            # Gửi thông báo match qua WebSocket nếu user chưa nhận được
            match_notification = {
                "type": "match_found",
                "data": {
                    "conversation_id": existing_conversation.id,
                    "conversation_type": existing_conversation.conversation_type,
                    "chat_url": f"/chat/{existing_conversation.id}",
                    "matched_user": {
                        "id": other_user.id,
                        "nickname": other_user.nickname
                    }
                }
            }
            
            # Gửi thông báo match cho user hiện tại
            await manager.send_personal_message(match_notification, current_user.id)
            
            print(f"🔄 User {current_user.id} already has active conversation {existing_conversation.id}, sent match notification")
            
            return SuccessResponse(
                success=True,
                message="Đã tìm thấy người phù hợp",
                data={
                    "conversation_id": existing_conversation.id,
                    "conversation_type": existing_conversation.conversation_type,
                    "chat_url": f"/chat/{existing_conversation.id}",
                    "matched_user": {
                        "id": other_user.id,
                        "nickname": other_user.nickname
                    }
                }
            )
        
        # Kiểm tra xem user đã đang trong trạng thái searching chưa
        if current_user.state == "searching":
            return SuccessResponse(
                success=True,
                message="Đang tìm kiếm...",
                data={"status": "searching"}
            )
        
        # Cập nhật trạng thái user
        current_user.state = "searching"
        db.commit()
        
        # Tìm kiếm ghép nối
        matching_service = MatchingService(db)
        match = matching_service.find_match(current_user, search_data.search_type)
        
        if match:
            try:
                # Tạo conversation
                conversation = matching_service.create_conversation(
                    current_user, match, search_data.search_type
                )
                
                # Thêm vào WebSocket connections
                manager.add_to_conversation(conversation.id, current_user.id)
                manager.add_to_conversation(conversation.id, match.id)
                
                # Tạo thông báo match cho cả 2 user
                match_notification_current = {
                    "type": "match_found",
                    "data": {
                        "conversation_id": conversation.id,
                        "conversation_type": conversation.conversation_type,
                        "chat_url": f"/chat/{conversation.id}",
                        "matched_user": {
                            "id": match.id,
                            "nickname": match.nickname
                        }
                    }
                }
                
                match_notification_other = {
                    "type": "match_found",
                    "data": {
                        "conversation_id": conversation.id,
                        "conversation_type": conversation.conversation_type,
                        "chat_url": f"/chat/{conversation.id}",
                        "matched_user": {
                            "id": current_user.id,
                            "nickname": current_user.nickname
                        }
                    }
                }
                
                # Gửi thông báo cho cả 2 user đồng thời
                await asyncio.gather(
                    manager.send_personal_message(match_notification_current, current_user.id),
                    manager.send_personal_message(match_notification_other, match.id),
                    return_exceptions=True
                )
                
                print(f"🎯 Match created: User {current_user.id} ({current_user.nickname}) matched with User {match.id} ({match.nickname})")
                print(f"   Conversation ID: {conversation.id}")
                print(f"   WebSocket notifications sent to both users")
                
                return SuccessResponse(
                    success=True,
                    message="Đã tìm thấy người phù hợp",
                    data={
                        "conversation_id": conversation.id,
                        "conversation_type": conversation.conversation_type,
                        "chat_url": f"/chat/{conversation.id}",
                        "matched_user": {
                            "id": match.id,
                            "nickname": match.nickname
                        }
                    }
                )
            except ValueError as e:
                # Nếu có lỗi khi tạo conversation (ví dụ: user đã được match với người khác)
                # Quay lại trạng thái searching và tiếp tục tìm kiếm
                current_user.state = "searching"
                db.commit()
                
                return SuccessResponse(
                    success=True,
                    message="Đang tìm kiếm...",
                    data={"status": "searching"}
                )
            except Exception as e:
                # Nếu có lỗi khác, quay về trạng thái waiting
                current_user.state = "waiting"
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Lỗi khi tạo conversation: {str(e)}"
                )
            
        else:
            return SuccessResponse(
                success=True,
                message="Đang tìm kiếm...",
                data={"status": "searching"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Đảm bảo user được đưa về trạng thái waiting nếu có lỗi
        try:
            current_user.state = "waiting"
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi server: {str(e)}"
        )

@app.post("/keep", response_model=SuccessResponse)
async def toggle_keep(
    keep_data: KeepRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Nhấn nút Keep"""
    conversation = db.query(Conversation).filter(
        Conversation.id == keep_data.conversation_id,
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc trò chuyện"
        )
    
    conversation.set_keep_status(current_user.id, keep_data.keep_status)
    conversation.last_activity = datetime.utcnow()
    db.commit()
    
    return SuccessResponse(
        success=True,
        message="Cập nhật trạng thái Keep thành công",
        data={
            "conversation_id": conversation.id,
            "keep_status": keep_data.keep_status,
            "both_kept": conversation.both_kept()
        }
    )

@app.post("/cancel-search", response_model=SuccessResponse)
async def cancel_search(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hủy tìm kiếm và quay về trạng thái waiting"""
    # Kiểm tra xem user có đang trong trạng thái searching không
    if current_user.state != "searching":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User không đang trong trạng thái tìm kiếm"
        )
    
    # Cập nhật trạng thái user về waiting
    current_user.state = "waiting"
    db.commit()
    
    return SuccessResponse(
        success=True,
        message="Đã hủy tìm kiếm"
    )

@app.post("/end", response_model=SuccessResponse)
async def end_conversation(
    end_data: EndRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Kết thúc cuộc trò chuyện"""
    conversation = db.query(Conversation).filter(
        Conversation.id == end_data.conversation_id,
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc trò chuyện"
        )
    
    # Kết thúc conversation
    matching_service = MatchingService(db)
    matching_service.end_conversation(conversation)
    
    # Gửi thông báo kết thúc cho tất cả user trong conversation
    message_to_send = {
        "type": "conversation_ended",
        "data": {
            "conversation_id": conversation.id,
            "ended_by": current_user.id,
            "redirect_to_waiting": True,
            "redirect_url": "/"
        }
    }
    
    # Gửi thông báo cho tất cả user trong conversation
    await manager.send_to_conversation(message_to_send, conversation.id)
    
    # Xóa khỏi WebSocket connections
    manager.remove_from_conversation(conversation.id, current_user.id)
    
    return SuccessResponse(
        success=True,
        message="Đã kết thúc cuộc trò chuyện"
    )

@app.get("/conversation/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tin nhắn của conversation"""
    # Kiểm tra user có trong conversation không
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        (Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id)
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc trò chuyện"
        )
    
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return messages

@app.get("/api/conversation/{conversation_id}", response_model=SuccessResponse)
async def get_conversation_info(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy thông tin conversation và user khác"""
    try:
        print(f"🔍 API request: User {current_user.id} ({current_user.username}) requesting conversation {conversation_id}")
        
        # Kiểm tra xem user có quyền xem conversation này không
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.is_active == True,
            ((Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id))
        ).first()
        
        if not conversation:
            print(f"❌ Conversation {conversation_id} not found or not active for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
        
        print(f"✅ Found conversation {conversation_id}: User1={conversation.user1_id}, User2={conversation.user2_id}")
        
        # Lấy thông tin user khác trong conversation
        other_user_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        if not other_user:
            print(f"❌ Other user {other_user_id} not found for conversation {conversation_id}")
            raise HTTPException(status_code=500, detail="Không tìm thấy thông tin user khác")
        
        print(f"✅ Found other user: {other_user.username} (ID: {other_user.id})")
        
        # Lấy thông tin keep status
        current_user_kept = conversation.user1_keep if conversation.user1_id == current_user.id else conversation.user2_keep
        both_kept = conversation.both_kept()
        
        # Lấy thông tin countdown
        countdown_time_left = conversation.get_countdown_time_left()
        countdown_expired = conversation.is_countdown_expired()
        
        response_data = {
            "conversation_id": conversation.id,
            "conversation_type": conversation.conversation_type,
            "matched_user": {
                "id": other_user.id,
                "nickname": other_user.nickname
            },
            "keep_status": {
                "current_user_kept": current_user_kept,
                "both_kept": both_kept
            },
            "countdown": {
                "time_left": countdown_time_left,
                "expired": countdown_expired,
                "start_time": conversation.countdown_start_time.isoformat() if conversation.countdown_start_time else None
            }
        }
        
        print(f"✅ Successfully returning conversation info for user {current_user.id}")
        return SuccessResponse(
            success=True,
            message="Thông tin conversation",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in get_conversation_info: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/api/conversation/{conversation_id}/countdown", response_model=SuccessResponse)
async def get_countdown_status(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy thông tin countdown của conversation"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.is_active == True,
            ((Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id))
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
        
        countdown_time_left = conversation.get_countdown_time_left()
        countdown_expired = conversation.is_countdown_expired()
        both_kept = conversation.both_kept()
        
        # Debug logging
        print(f"🔍 Countdown API request for conversation {conversation_id}:")
        print(f"   User: {current_user.username} (ID: {current_user.id})")
        print(f"   Time left: {countdown_time_left}s")
        print(f"   Expired: {countdown_expired}")
        print(f"   Both kept: {both_kept}")
        print(f"   Start time: {conversation.countdown_start_time}")
        
        return SuccessResponse(
            success=True,
            message="Thông tin countdown",
            data={
                "conversation_id": conversation.id,
                "time_left": countdown_time_left,
                "expired": countdown_expired,
                "both_kept": both_kept,
                "start_time": conversation.countdown_start_time.isoformat() if conversation.countdown_start_time else None,
                "debug_info": {
                    "user_id": current_user.id,
                    "conversation_type": conversation.conversation_type,
                    "user1_keep": conversation.user1_keep,
                    "user2_keep": conversation.user2_keep
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in countdown endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint cho real-time communication"""
    # Xác thực user trước khi kết nối WebSocket
    try:
        # Lấy token từ query parameter hoặc header
        token = websocket.query_params.get("token")
        if not token:
            # Thử lấy từ header
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return
        
        # Verify token
        from app.auth import verify_token
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
        
        username = payload.get("sub")
        if not username:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
        
        # Verify user exists and matches the user_id in URL
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username, User.id == user_id).first()
            if not user:
                await websocket.close(code=4001, reason="User not found or ID mismatch")
                return
        finally:
            db.close()
        
        # Kết nối WebSocket
        handler = WebSocketHandler()
        await handler.handle_websocket(websocket, user_id)
        
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal server error")
        except:
            pass

@app.get("/api/searching-count")
async def get_searching_count(db: Session = Depends(get_db)):
    """Lấy số người đang tìm kiếm"""
    try:
        # Đếm số user đang trong trạng thái searching
        searching_users = db.query(User).filter(
            User.state == "searching"
        ).count()
        
        return {
            "success": True,
            "data": {
                "searching_count": searching_users
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy số người đang tìm kiếm: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Mapmo.vn"}

@app.post("/api/admin/cleanup-expired", response_model=SuccessResponse)
async def cleanup_expired_conversations_manual(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint để manually cleanup các conversation đã hết countdown (cho admin)"""
    try:
        # Tìm các conversation đã hết countdown và chưa được keep
        expired_conversations = db.query(Conversation).filter(
            Conversation.is_active == True,
            Conversation.user1_keep == False,
            Conversation.user2_keep == False
        ).all()
        
        cleaned_count = 0
        matching_service = MatchingService(db)
        
        for conversation in expired_conversations:
            if conversation.is_countdown_expired():
                # Kết thúc conversation
                matching_service.end_conversation(conversation)
                cleaned_count += 1
                
                # Gửi thông báo kết thúc cho tất cả user trong conversation
                message_to_send = {
                    "type": "conversation_ended",
                    "data": {
                        "conversation_id": conversation.id,
                        "ended_by": "system",
                        "reason": "countdown_expired",
                        "redirect_to_waiting": True,
                        "redirect_url": "/"
                    }
                }
                
                # Gửi thông báo cho tất cả user trong conversation
                await manager.send_to_conversation(message_to_send, conversation.id)
                
                # Xóa khỏi WebSocket connections
                manager.remove_from_conversation(conversation.id, conversation.user1_id)
                manager.remove_from_conversation(conversation.id, conversation.user2_id)
        
        return SuccessResponse(
            success=True,
            message=f"Đã cleanup {cleaned_count} conversation hết countdown"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cleanup: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 