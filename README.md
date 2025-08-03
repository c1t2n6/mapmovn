# Mapmo.vn - Anonymous Web Chat

Ứng dụng web chat ẩn danh cho phép người dùng trò chuyện và kết nối với nhau dựa trên sở thích và mong muốn.

## Tính năng chính

- **Đăng ký/Đăng nhập**: Hệ thống xác thực an toàn
- **Thiết lập hồ sơ**: 4 bước thiết lập thông tin cá nhân
- **Ghép nối thông minh**: Thuật toán ghép nối dựa trên sở thích và mong muốn
- **Chat ẩn danh**: Trò chuyện real-time với WebSocket
- **Countdown Timer**: Đếm ngược 5 phút cho mỗi cuộc trò chuyện
- **Nút Keep**: Duy trì kết nối giữa hai người dùng
- **Tự động xóa phòng**: Kết thúc và xóa phòng khi countdown hết thời gian
- **Giao diện đẹp**: Thiết kế hiện đại với hiệu ứng động

## Công nghệ sử dụng

### Backend
- **FastAPI**: Framework web hiện đại cho Python
- **SQLAlchemy**: ORM cho database
- **SQLite**: Database (có thể thay đổi sang PostgreSQL cho production)
- **WebSocket**: Giao tiếp real-time
- **JWT**: Xác thực token
- **bcrypt**: Mã hóa mật khẩu

### Frontend
- **HTML5/CSS3**: Giao diện người dùng
- **JavaScript (ES6+)**: Logic client-side
- **WebSocket API**: Kết nối real-time
- **Responsive Design**: Tương thích mobile và desktop

## Cài đặt và chạy

### Yêu cầu hệ thống
- Python 3.8+
- pip (Python package manager)

### Bước 1: Clone repository
```bash
git clone <repository-url>
cd MM_Grok
```

### Bước 2: Tạo virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Bước 4: Chạy ứng dụng
```bash
# Chạy với uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Hoặc chạy trực tiếp
python run.py
```

### Bước 5: Truy cập ứng dụng
Mở trình duyệt và truy cập: `http://localhost:8000`

## Deployment lên Render

### Bước 1: Chuẩn bị
Đảm bảo các file sau đã có trong project:
- `render.yaml` - Cấu hình Render
- `Procfile` - Lệnh khởi động
- `runtime.txt` - Phiên bản Python
- `requirements.txt` - Dependencies

### Bước 2: Push code lên GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### Bước 3: Deploy trên Render
1. Đăng nhập vào [Render](https://render.com)
2. Tạo "New Web Service"
3. Kết nối với GitHub repository
4. Chọn branch `main`
5. Cấu hình:
   - **Name**: `mapmo-vn`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Bước 4: Cấu hình Environment Variables
Trong Render Dashboard, thêm các biến môi trường:
- `SECRET_KEY`: Tạo key bảo mật
- `DATABASE_URL`: `sqlite:///./mapmo.db`
- `DEBUG`: `False`
- `ALGORITHM`: `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `30`

### Bước 5: Deploy
Click "Create Web Service" và đợi deployment hoàn tất.

## Cấu trúc dự án

```
MM_Grok/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app và endpoints
│   ├── database.py          # Cấu hình database
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication logic
│   ├── matching.py          # Thuật toán ghép nối
│   └── websocket_manager.py # WebSocket management
├── static/
│   ├── css/
│   │   └── style.css        # Stylesheet chính
│   ├── js/
│   │   └── app.js           # JavaScript chính
│   └── index.html           # HTML template
├── requirements.txt         # Python dependencies
└── README.md               # Hướng dẫn này
```

## API Endpoints

### Authentication
- `POST /register` - Đăng ký tài khoản mới
- `POST /login` - Đăng nhập
- `POST /logout` - Đăng xuất

### Profile
- `PUT /profile` - Cập nhật hồ sơ người dùng
- `GET /profile/options` - Lấy danh sách tùy chọn

### Chat & Matching
- `POST /search` - Bắt đầu tìm kiếm ghép nối
- `POST /keep` - Cập nhật trạng thái Keep
- `POST /end` - Kết thúc cuộc trò chuyện
- `GET /conversation/{id}/messages` - Lấy tin nhắn

### WebSocket
- `WS /ws/{user_id}` - Kết nối WebSocket cho real-time chat

## Luồng sử dụng

### 1. Đăng ký và Đăng nhập
- Người dùng đăng ký với username và password
- Đăng nhập để truy cập ứng dụng

### 2. Thiết lập hồ sơ (4 bước)
- **Bước 1**: Thông tin cơ bản (nickname, ngày sinh, giới tính)
- **Bước 2**: Mong muốn gặp ai (Nam, Nữ, Tất cả)
- **Bước 3**: Mục đích tìm kiếm (7 lựa chọn)
- **Bước 4**: Sở thích (chọn tối đa 5 từ 15 lựa chọn)

### 3. Phòng chờ
- Hiển thị 2 nút: Chat và Voice Call
- Người dùng chọn cách muốn kết nối

### 4. Ghép nối
- Hệ thống tìm người phù hợp dựa trên thuật toán
- Ưu tiên sở thích và mong muốn chung
- Fallback sang ghép ngẫu nhiên nếu không tìm được

### 5. Chat
- Giao diện chat real-time
- Hiển thị "đang nhập" khi đối phương gõ
- Nút Keep để duy trì kết nối
- Nút End để kết thúc

## Thuật toán ghép nối

### Điểm phù hợp được tính dựa trên:
1. **Preference matching** (40%): Giới tính mong muốn
2. **Goal compatibility** (30%): Mục đích tìm kiếm
3. **Common interests** (30%): Sở thích chung

### Phân loại ghép nối:
- **Best matches** (≥80%): Ghép nối tối ưu
- **Good matches** (50-79%): Ghép nối tốt
- **Random matches** (<50%): Ghép ngẫu nhiên

## Tính năng đặc biệt

### Countdown Timer & Tự động xóa phòng
- **Countdown 5 phút**: Mỗi cuộc trò chuyện có thời gian 5 phút
- **Tự động xóa**: Khi countdown hết, phòng chat tự động bị xóa
- **Background task**: Hệ thống tự động kiểm tra và xóa phòng hết thời gian
- **Sync real-time**: Frontend đồng bộ với server mỗi 30 giây

### Nút Keep
- Một người nhấn: Trái tim đầy một nửa 💗
- Cả hai nhấn: Trái tim đầy hoàn toàn 💖
- Duy trì cuộc trò chuyện không bị tự hủy
- **Dừng countdown**: Khi cả 2 keep, countdown dừng lại vĩnh viễn

### Voice Call (Tương lai)
- Mở khóa sau 5 phút chat
- Tích hợp WebRTC cho voice call
- Hiệu ứng giọng nói và nền động

### Bảo mật
- Mật khẩu được mã hóa bằng bcrypt
- JWT token cho xác thực
- Không lưu trữ thông tin cá nhân thật
- Hệ thống báo cáo hành vi xấu

## Phát triển

### Thêm tính năng mới
1. Tạo model mới trong `app/models.py`
2. Thêm schema trong `app/schemas.py`
3. Tạo endpoint trong `app/main.py`
4. Cập nhật frontend trong `static/js/app.js`

### Database migrations
```bash
# Tạo migration
alembic revision --autogenerate -m "Description"

# Chạy migration
alembic upgrade head
```

### Testing
```bash
# Chạy tests
pytest

# Chạy với coverage
pytest --cov=app

# Test tính năng countdown và xóa phòng
python test_countdown_cleanup.py
```

## Deployment

### Production setup
1. Thay đổi database từ SQLite sang PostgreSQL
2. Cấu hình environment variables
3. Sử dụng nginx làm reverse proxy
4. Setup SSL certificate
5. Cấu hình logging và monitoring

### Environment variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/mapmo
SECRET_KEY=your-secret-key-here
DEBUG=False
```

## Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## License

MIT License - xem file LICENSE để biết thêm chi tiết.

## Hỗ trợ

Nếu gặp vấn đề hoặc có câu hỏi, vui lòng tạo issue trên GitHub repository.

---

**Mapmo.vn** - Kết nối ẩn danh, khám phá mối quan hệ mới 🌟 