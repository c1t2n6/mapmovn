# 🕐 Countdown Timer Feature - Mapmo.vn

## Tổng quan

Chức năng countdown timer được thêm vào chat room để tạo áp lực thời gian và khuyến khích người dùng đưa ra quyết định nhanh chóng về việc có muốn tiếp tục cuộc trò chuyện hay không.

## Tính năng chính

### ⏰ Countdown Timer 5 phút
- **Thời gian**: 5 phút (300 giây) đếm ngược
- **Hiển thị**: Thay thế chữ "Đã kết nối" bằng đồng hồ đếm ngược
- **Format**: `⏰ MM:SS` (ví dụ: `⏰ 4:59`)

### 🔄 Server-Synchronized Countdown
- **Database Storage**: Thời gian bắt đầu được lưu trong database
- **Cross-User Sync**: Đồng bộ giữa 2 user trong cùng conversation
- **Reload Persistence**: Không bị reset khi reload trang
- **Real-time Sync**: Tự động sync với server mỗi 30 giây

### 🎨 Visual Feedback
- **Màu xanh dương** (#2196F3): Thời gian còn nhiều (> 1 phút)
- **Màu cam** (#ffa726): Cảnh báo khi còn 1 phút
- **Màu đỏ** (#ff6b6b): Nguy hiểm khi còn 30 giây
- **Animation**: Pulse effect tăng dần theo mức độ khẩn cấp

### ❤️ Keep Button Integration
- **Cả 2 Keep**: Countdown dừng lại, hiển thị "Đã kết nối" màu xanh
- **Chỉ 1 Keep**: Countdown tiếp tục chạy
- **Không Keep**: Countdown chạy đến hết thời gian

### 🔄 Auto End Conversation
- **Tự động kết thúc**: Khi countdown về 0
- **Thông báo**: "Hết thời gian! Cuộc trò chuyện sẽ kết thúc."
- **Redirect**: Về sảnh chờ sau 2 giây

## Cách hoạt động

### 1. Database Schema
```sql
ALTER TABLE conversations 
ADD COLUMN countdown_start_time DATETIME DEFAULT CURRENT_TIMESTAMP;
```

### 2. Server-Side Countdown Logic
```python
def get_countdown_time_left(self):
    """Tính toán thời gian còn lại của countdown"""
    now = datetime.now(timezone.utc)
    elapsed = (now - self.countdown_start_time).total_seconds()
    time_left = 300 - elapsed  # 300 giây = 5 phút
    return max(0, int(time_left))
```

### 3. Client-Side Sync
```javascript
// Sync với server mỗi 30 giây
this.serverSyncInterval = setInterval(() => {
    this.syncCountdownWithServer();
}, 30000);

// Tính toán thời gian từ server
calculateTimeLeftFromServer() {
    const startTime = new Date(this.countdownStartTime);
    const now = new Date();
    const elapsed = Math.floor((now - startTime) / 1000);
    const timeLeft = this.countdownDuration - elapsed;
    return Math.max(0, timeLeft);
}
```

## API Endpoints

### GET `/api/conversation/{conversation_id}`
Trả về thông tin keep status và countdown:
```json
{
    "success": true,
    "data": {
        "conversation_id": 123,
        "conversation_type": "chat",
        "matched_user": {...},
        "keep_status": {
            "current_user_kept": true,
            "both_kept": false
        },
        "countdown": {
            "time_left": 245,
            "expired": false,
            "start_time": "2024-01-01T12:00:00Z"
        }
    }
}
```

### GET `/api/conversation/{conversation_id}/countdown`
Lấy thông tin countdown:
```json
{
    "success": true,
    "data": {
        "conversation_id": 123,
        "time_left": 245,
        "expired": false,
        "both_kept": false,
        "start_time": "2024-01-01T12:00:00Z"
    }
}
```

### POST `/keep`
Cập nhật keep status và trả về:
```json
{
    "success": true,
    "data": {
        "conversation_id": 123,
        "keep_status": true,
        "both_kept": true
    }
}
```

## WebSocket Messages

### Keep Status Update
```json
{
    "type": "keep_status",
    "data": {
        "keep_status": true,
        "both_kept": true
    }
}
```

## CSS Classes

### Countdown Animation
```css
.countdown {
    animation: countdownPulse 1s ease-in-out infinite;
}

.countdown.warning {
    animation: countdownWarning 0.5s ease-in-out infinite;
}

.countdown.danger {
    animation: countdownDanger 0.3s ease-in-out infinite;
}
```

## Migration

### Chạy migration script
```bash
python migrate_countdown.py
```

### Build script tự động
```bash
# build.sh sẽ tự động chạy migration
chmod +x build.sh && ./build.sh
```

## Testing

### Chạy test script đồng bộ
```bash
python test_sync_countdown.py
```

### Test manual trên frontend
1. Mở 2 tab browser
2. Đăng nhập với 2 user khác nhau
3. Vào chat room và quan sát countdown
4. Reload trang và kiểm tra countdown không bị reset
5. Test Keep button
6. Đợi countdown kết thúc

## Cấu hình

### Thời gian countdown
```javascript
this.countdownDuration = 5 * 60; // 5 phút = 300 giây
```

### Sync interval
```javascript
// Sync với server mỗi 30 giây
setInterval(() => {
    this.syncCountdownWithServer();
}, 30000);
```

### Màu sắc và animation
- Có thể điều chỉnh trong `updateCountdownDisplay()`
- CSS animations có thể tùy chỉnh trong `style.css`

## Lưu ý quan trọng

1. **Database Migration**: Cần chạy migration để thêm cột `countdown_start_time`
2. **Server-Side Time**: Countdown dựa trên thời gian server, không phải client
3. **Cross-User Sync**: Tất cả user trong conversation thấy cùng thời gian
4. **Reload Persistence**: Countdown không bị reset khi reload trang
5. **Real-time Updates**: WebSocket cập nhật keep status real-time
6. **Auto Cleanup**: Countdown được dừng khi logout hoặc kết thúc conversation

## Troubleshooting

### Countdown không đồng bộ
- Kiểm tra server time
- Đảm bảo migration đã chạy thành công
- Kiểm tra `countdown_start_time` trong database

### Countdown bị reset khi reload
- Kiểm tra `countdownStartTime` từ API response
- Đảm bảo `calculateTimeLeftFromServer()` hoạt động đúng
- Kiểm tra timezone settings

### Keep button không hoạt động
- Kiểm tra API response
- Đảm bảo conversation_id đúng
- Kiểm tra authentication token

### Countdown không dừng khi Keep
- Kiểm tra `both_kept` status từ API
- Đảm bảo WebSocket message được nhận
- Kiểm tra `setBothKeptStatus()` method 