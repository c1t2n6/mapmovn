from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime

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
        
        # Thêm vào WebSocket connections nếu chưa có
        manager.add_to_conversation(existing_conversation.id, current_user.id)
        
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
            
            # Gửi thông báo match qua WebSocket cho cả 2 user với URL redirect
            match_notification = {
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
            
            # Gửi thông báo cho user hiện tại
            await manager.send_personal_message(match_notification, current_user.id)
            
            # Gửi thông báo cho user được match
            await manager.send_personal_message(match_notification, match.id)
            
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
        
    else:
        return SuccessResponse(
            success=True,
            message="Đang tìm kiếm...",
            data={"status": "searching"}
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
    # Kiểm tra xem user có quyền xem conversation này không
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.is_active == True,
        ((Conversation.user1_id == current_user.id) | (Conversation.user2_id == current_user.id))
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    
    # Lấy thông tin user khác trong conversation
    other_user_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    other_user = db.query(User).filter(User.id == other_user_id).first()
    
    return SuccessResponse(
        success=True,
        message="Thông tin conversation",
        data={
            "conversation_id": conversation.id,
            "conversation_type": conversation.conversation_type,
            "matched_user": {
                "id": other_user.id,
                "nickname": other_user.nickname
            }
        }
    )

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    """WebSocket endpoint cho real-time communication"""
    handler = WebSocketHandler(db)
    await handler.handle_websocket(websocket, user_id)

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

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 