# 🕐 Countdown Timer Feature - Mapmo.vn

## Tổng quan

Chức năng countdown timer được thêm vào chat room để tạo áp lực thời gian và khuyến khích người dùng đưa ra quyết định nhanh chóng về việc có muốn tiếp tục cuộc trò chuyện hay không.

## Tính năng chính

### ⏰ Countdown Timer 5 phút
- **Thời gian**: 5 phút (300 giây) đếm ngược
- **Hiển thị**: Thay thế chữ "Đã kết nối" bằng đồng hồ đếm ngược
- **Format**: `⏰ MM:SS` (ví dụ: `⏰ 4:59`)

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

### 1. Khi vào Chat Room
```javascript
// Tự động bắt đầu countdown
this.startCountdown();
```

### 2. Countdown Logic
```javascript
// Cập nhật mỗi giây
setInterval(() => {
    this.countdownTimeLeft--;
    this.updateCountdownDisplay();
    
    if (this.countdownTimeLeft <= 0) {
        this.endCountdown();
    }
}, 1000);
```

### 3. Keep Button Logic
```javascript
// Khi cả 2 đã keep
if (data.both_kept) {
    this.setBothKeptStatus(true);
    this.stopCountdown();
    // Hiển thị "Đã kết nối"
}
```

## API Endpoints

### GET `/api/conversation/{conversation_id}`
Trả về thông tin keep status:
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
        }
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

## Testing

### Chạy test script
```bash
python test_countdown_timer.py
```

### Test manual trên frontend
1. Mở 2 tab browser
2. Đăng nhập với 2 user khác nhau
3. Vào chat room và quan sát countdown
4. Test Keep button
5. Đợi countdown kết thúc

## Cấu hình

### Thời gian countdown
```javascript
this.countdownDuration = 5 * 60; // 5 phút = 300 giây
```

### Màu sắc và animation
- Có thể điều chỉnh trong `updateCountdownDisplay()`
- CSS animations có thể tùy chỉnh trong `style.css`

## Lưu ý quan trọng

1. **Dừng countdown**: Khi cả 2 người đã keep
2. **Tự động kết thúc**: Khi countdown về 0
3. **Cleanup**: Countdown được dừng khi logout hoặc kết thúc conversation
4. **Real-time**: WebSocket cập nhật keep status real-time
5. **Persistent**: Keep status được lưu trong database

## Troubleshooting

### Countdown không hiển thị
- Kiểm tra console log
- Đảm bảo `showChatInterface()` được gọi
- Kiểm tra WebSocket connection

### Keep button không hoạt động
- Kiểm tra API response
- Đảm bảo conversation_id đúng
- Kiểm tra authentication token

### Countdown không dừng khi Keep
- Kiểm tra `both_kept` status từ API
- Đảm bảo WebSocket message được nhận
- Kiểm tra `setBothKeptStatus()` method 