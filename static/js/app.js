// Mapmo.vn - Anonymous Web Chat Application
class MapmoApp {
    constructor() {
        this.currentUser = null;
        this.currentConversation = null;
        this.websocket = null;
        this.pendingTempMessage = null; // Tin nhắn tạm thời đang chờ
        this.typingTimeout = null; // Timeout cho typing indicator
        
        // Countdown timer properties
        this.countdownTimer = null;
        this.countdownInterval = null;
        this.countdownDuration = 5 * 60; // 5 phút = 300 giây
        this.countdownTimeLeft = this.countdownDuration;
        this.bothKept = false; // Trạng thái cả 2 người đã keep
        this.countdownStartTime = null; // Thời gian bắt đầu từ server
        this.serverSyncInterval = null; // Interval để sync với server
        
        this.init();
    }
    
    init() {
        this.checkAuth();
        this.setupEventListeners();
        this.createParticles();
    }
    
    createParticles() {
        const particlesContainer = document.createElement('div');
        particlesContainer.className = 'particles';
        document.body.appendChild(particlesContainer);
        
        for (let i = 0; i < 50; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 6 + 's';
            particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
            particlesContainer.appendChild(particle);
        }
    }
    
    async checkAuth() {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const response = await fetch('/api/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const userData = await response.json();
                    this.currentUser = userData;
                    
                    // Kiểm tra xem có conversation ID trong URL không
                    const pathParts = window.location.pathname.split('/');
                    const conversationId = pathParts[pathParts.length - 1];
                    
                    if (pathParts.includes('chat') && conversationId && !isNaN(conversationId)) {
                        await this.loadConversationFromUrl(parseInt(conversationId));
                    } else {
                        this.showMainInterface();
                    }
                } else {
                    this.showLoginForm();
                }
            } catch (error) {
                this.showLoginForm();
            }
        } else {
            this.showLoginForm();
        }
    }
    
    async loadConversationFromUrl(conversationId) {
        // Load conversation từ URL
        try {
            const response = await fetch(`/api/conversation/${conversationId}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentConversation = {
                    conversation_id: conversationId,
                    conversation_type: data.data.conversation_type,
                    matched_user: data.data.matched_user
                };
                
                // Cập nhật trạng thái keep
                if (data.data.keep_status) {
                    this.keepStatus = data.data.keep_status.current_user_kept;
                    this.setBothKeptStatus(data.data.keep_status.both_kept);
                }
                
                // Cập nhật thông tin countdown từ server
                if (data.data.countdown) {
                    this.countdownTimeLeft = data.data.countdown.time_left;
                    this.countdownStartTime = data.data.countdown.start_time;
                    
                    console.log('📊 Countdown info from server:', {
                        time_left: this.countdownTimeLeft,
                        start_time: this.countdownStartTime,
                        expired: data.data.countdown.expired,
                        both_kept: data.data.countdown.both_kept
                    });
                    
                    // Nếu countdown đã hết thời gian, kết thúc conversation
                    if (data.data.countdown.expired && !this.bothKept) {
                        this.showError('Hết thời gian! Cuộc trò chuyện sẽ kết thúc.');
                        setTimeout(() => {
                            this.endConversation();
                        }, 2000);
                        return;
                    }
                    
                    // Nếu cả 2 đã keep, dừng countdown
                    if (data.data.countdown.both_kept) {
                        this.setBothKeptStatus(true);
                    }
                }
                
                this.showChatInterface();
            } else if (response.status === 404) {
                this.showError('Phòng chat không tồn tại hoặc đã bị đóng');
                this.showMainInterface();
            } else if (response.status === 401) {
                this.showError('Phiên đăng nhập đã hết hạn');
                this.showLoginForm();
            } else {
                this.showError('Không thể load phòng chat');
                this.showMainInterface();
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Lỗi kết nối');
            this.showMainInterface();
        }
    }
    
    setupEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.id === 'loginBtn') {
                e.preventDefault();
                this.handleLogin();
            }
            if (e.target.id === 'registerBtn') {
                e.preventDefault();
                this.handleRegister();
            }
            if (e.target.id === 'logoutBtn') {
                e.preventDefault();
                this.handleLogout();
            }
            if (e.target.id === 'chatBtn' || e.target.closest('#chatBtn')) {
                e.preventDefault();
                this.startSearch('chat');
            }
            if (e.target.id === 'voiceBtn' || e.target.closest('#voiceBtn')) {
                e.preventDefault();
                this.startSearch('voice');
            }
        });
    }
    
    showLoginForm() {
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="welcome-section">
                <h1>Mapmo.vn</h1>
                <p>Kết nối ẩn danh, khám phá mối quan hệ mới</p>
            </div>
            
            <div class="form-container">
                <h2 class="form-title">Đăng nhập</h2>
                <form id="loginForm">
                    <div class="form-group">
                        <label class="form-label">Tên đăng nhập</label>
                        <input type="text" id="username" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Mật khẩu</label>
                        <input type="password" id="password" class="form-input" required>
                    </div>
                    <button type="submit" id="loginBtn" class="btn btn-primary">Đăng nhập</button>
                </form>
                <p style="text-align: center; margin-top: 20px;">
                    Chưa có tài khoản? <a href="#" id="showRegister">Đăng ký ngay</a>
                </p>
            </div>
        `;
        
        document.getElementById('showRegister').addEventListener('click', (e) => {
            e.preventDefault();
            this.showRegisterForm();
        });
    }
    
    showRegisterForm() {
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="welcome-section">
                <h1>Mapmo.vn</h1>
                <p>Tham gia cộng đồng chat ẩn danh</p>
            </div>
            
            <div class="form-container">
                <h2 class="form-title">Đăng ký</h2>
                <form id="registerForm">
                    <div class="form-group">
                        <label class="form-label">Tên đăng nhập</label>
                        <input type="text" id="regUsername" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Mật khẩu</label>
                        <input type="password" id="regPassword" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Xác nhận mật khẩu</label>
                        <input type="password" id="confirmPassword" class="form-input" required>
                    </div>
                    <button type="submit" id="registerBtn" class="btn btn-primary">Đăng ký</button>
                </form>
                <p style="text-align: center; margin-top: 20px;">
                    Đã có tài khoản? <a href="#" id="showLogin">Đăng nhập</a>
                </p>
            </div>
        `;
        
        document.getElementById('showLogin').addEventListener('click', (e) => {
            e.preventDefault();
            this.showLoginForm();
        });
    }
    
    showProfileSetup() {
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="welcome-section">
                <h1>Hoàn thành hồ sơ</h1>
                <p>Hãy chia sẻ một chút về bản thân để tìm được người phù hợp</p>
            </div>
            
            <div class="form-container">
                <h2 class="form-title">Thông tin cá nhân</h2>
                <form id="profileForm">
                    <div class="form-group">
                        <label class="form-label">Biệt danh</label>
                        <input type="text" id="nickname" class="form-input" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Ngày sinh</label>
                        <input type="date" id="dob" class="form-input" required>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Giới tính</label>
                        <select id="gender" class="form-input" required>
                            <option value="">Chọn giới tính</option>
                            <option value="Nam">Nam</option>
                            <option value="Nữ">Nữ</option>
                            <option value="Khác">Khác</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Tìm kiếm</label>
                        <select id="preference" class="form-input" required>
                            <option value="">Chọn đối tượng</option>
                            <option value="Nam">Nam</option>
                            <option value="Nữ">Nữ</option>
                            <option value="Tất cả">Tất cả</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Mục đích</label>
                        <select id="goal" class="form-input" required>
                            <option value="">Chọn mục đích</option>
                            <option value="Một mối quan hệ nhẹ nhàng, vui vẻ">Một mối quan hệ nhẹ nhàng, vui vẻ</option>
                            <option value="Một mối quan hệ nghiêm túc">Một mối quan hệ nghiêm túc</option>
                            <option value="Chưa chắc, muốn khám phá thêm">Chưa chắc, muốn khám phá thêm</option>
                            <option value="Kết hôn">Kết hôn</option>
                            <option value="Bạn đời lâu dài">Bạn đời lâu dài</option>
                            <option value="Mối quan hệ mở">Mối quan hệ mở</option>
                            <option value="Kết bạn mới thôi 🥰">Kết bạn mới thôi 🥰</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">Sở thích (chọn tối đa 5)</label>
                        <div id="interestsContainer" class="interests-container">
                            <label class="interest-item">
                                <input type="checkbox" value="Tập gym 💪"> Tập gym 💪
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Nhảy nhót 💃"> Nhảy nhót 💃
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Chụp ảnh 📷"> Chụp ảnh 📷
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Uống cà phê ☕"> Uống cà phê ☕
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Du lịch ✈️"> Du lịch ✈️
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Chơi game 🎮"> Chơi game 🎮
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Đọc sách 📚"> Đọc sách 📚
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Nghe nhạc 🎧"> Nghe nhạc 🎧
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Làm tình nguyện ❤️"> Làm tình nguyện ❤️
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Xem phim 🍿"> Xem phim 🍿
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Leo núi 🏔️"> Leo núi 🏔️
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Nghệ thuật 🎨"> Nghệ thuật 🎨
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Ăn ngon 🥘"> Ăn ngon 🥘
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Tâm linh ✨"> Tâm linh ✨
                            </label>
                            <label class="interest-item">
                                <input type="checkbox" value="Thời trang 👗"> Thời trang 👗
                            </label>
                        </div>
                    </div>
                    
                    <button type="submit" id="saveProfileBtn" class="btn btn-primary">Lưu hồ sơ</button>
                </form>
            </div>
        `;
        
        // Thêm event listener cho form
        document.getElementById('profileForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleProfileSetup();
        });
        
        // Giới hạn số lượng sở thích được chọn
        const checkboxes = document.querySelectorAll('#interestsContainer input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const checkedBoxes = document.querySelectorAll('#interestsContainer input[type="checkbox"]:checked');
                if (checkedBoxes.length > 5) {
                    checkbox.checked = false;
                    this.showError('Chỉ được chọn tối đa 5 sở thích');
                }
            });
        });
    }
    
    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showError('Vui lòng nhập đầy đủ thông tin');
            return;
        }
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('access_token', data.data.access_token);
                this.currentUser = data.data.user;
                
                if (data.data.user.profile_completed) {
                    this.showMainInterface();
                } else {
                    this.showProfileSetup();
                }
            } else {
                this.showError(data.detail || 'Đăng nhập thất bại');
            }
        } catch (error) {
            this.showError('Lỗi kết nối');
        }
    }
    
    async handleRegister() {
        const username = document.getElementById('regUsername').value;
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (!username || !password || !confirmPassword) {
            this.showError('Vui lòng nhập đầy đủ thông tin');
            return;
        }
        
        if (password !== confirmPassword) {
            this.showError('Mật khẩu xác nhận không khớp');
            return;
        }
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, confirm_password: confirmPassword })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('Đăng ký thành công! Vui lòng đăng nhập');
                setTimeout(() => this.showLoginForm(), 2000);
            } else {
                this.showError(data.detail || 'Đăng ký thất bại');
            }
        } catch (error) {
            this.showError('Lỗi kết nối');
        }
    }
    
    async handleProfileSetup() {
        const nickname = document.getElementById('nickname').value;
        const dob = document.getElementById('dob').value;
        const gender = document.getElementById('gender').value;
        const preference = document.getElementById('preference').value;
        const goal = document.getElementById('goal').value;
        
        // Lấy danh sách sở thích đã chọn
        const checkedInterests = document.querySelectorAll('#interestsContainer input[type="checkbox"]:checked');
        const interests = Array.from(checkedInterests).map(cb => cb.value);
        
        if (!nickname || !dob || !gender || !preference || !goal) {
            this.showError('Vui lòng điền đầy đủ thông tin');
            return;
        }
        
        if (interests.length === 0) {
            this.showError('Vui lòng chọn ít nhất 1 sở thích');
            return;
        }
        
        if (interests.length > 5) {
            this.showError('Chỉ được chọn tối đa 5 sở thích');
            return;
        }
        
        try {
            const response = await fetch('/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    nickname,
                    dob: new Date(dob).toISOString(),
                    gender,
                    preference,
                    goal,
                    interests
                })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('Cập nhật hồ sơ thành công!');
                // Cập nhật thông tin user hiện tại
                this.currentUser.nickname = nickname;
                setTimeout(() => this.showMainInterface(), 1500);
            } else {
                this.showError(data.detail || 'Cập nhật hồ sơ thất bại');
            }
        } catch (error) {
            this.showError('Lỗi kết nối');
        }
    }
    
    showMainInterface() {
        // Dừng interval cập nhật số người đang tìm kiếm nếu có
        if (this.searchingCountInterval) {
            clearInterval(this.searchingCountInterval);
            this.searchingCountInterval = null;
        }
        
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="welcome-section">
                <h1>Chào ${this.currentUser.nickname || this.currentUser.username}!</h1>
                <p>Sẵn sàng kết nối chưa?</p>
            </div>
            
            <div class="waiting-room">
                <h2>Phòng chờ</h2>
                <p>Chọn cách bạn muốn kết nối</p>
                
                <div class="action-buttons">
                    <a href="#" id="chatBtn" class="action-btn">
                        <i>💬</i>
                        <span>Chat</span>
                    </a>
                    <a href="#" id="voiceBtn" class="action-btn">
                        <i>📞</i>
                        <span>Voice Call</span>
                    </a>
                </div>
                
                <button id="logoutBtn" class="btn btn-secondary" style="margin-top: 30px;">Đăng xuất</button>
            </div>
        `;
    }
    
    async startSearch(searchType) {
        // Hiển thị màn hình tìm kiếm ngay lập tức
        await this.showSearching(searchType);
        
        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ search_type: searchType })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                if (data.data.status === 'searching') {
                    // Đã hiển thị searching UI rồi, không cần làm gì thêm
                    // WebSocket sẽ xử lý khi có match
                } else if (data.data.conversation_id) {
                    // Nếu có conversation_id, có nghĩa là đã match
                    this.currentConversation = data.data;
                    this.showChatInterface();
                }
            } else {
                this.showError(data.detail || 'Tìm kiếm thất bại');
                // Quay lại màn hình chính nếu có lỗi
                this.showMainInterface();
            }
        } catch (error) {
            this.showError('Lỗi kết nối');
            // Quay lại màn hình chính nếu có lỗi
            this.showMainInterface();
        }
    }
    
    async showSearching(searchType) {
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="welcome-section">
                <h1>Đang tìm kiếm...</h1>
                <p>${searchType === 'chat' ? 'Tìm người để chat' : 'Tìm người để gọi voice'}</p>
            </div>
            
            <div class="waiting-room">
                <div class="searching-animation">
                    <div class="pulse-circle"></div>
                    <div class="searching-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <h2>Đang tìm kiếm người phù hợp</h2>
                <p>Vui lòng chờ trong giây lát</p>
                
                <div class="searching-stats">
                    <div class="stats-item">
                        <span class="stats-icon">👥</span>
                        <span class="stats-text">Đang tìm kiếm: <span id="searchingCount">...</span> người</span>
                    </div>
                </div>
                
                <button id="cancelSearchBtn" class="btn btn-secondary" style="margin-top: 30px;">Hủy tìm kiếm</button>
            </div>
        `;
        
        document.getElementById('cancelSearchBtn').addEventListener('click', async () => {
            try {
                // Gọi API để hủy tìm kiếm
                const response = await fetch('/cancel-search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });
                
                if (response.ok) {
                    console.log('Đã hủy tìm kiếm thành công');
                } else {
                    console.error('Lỗi khi hủy tìm kiếm:', response.text);
                }
            } catch (error) {
                console.error('Lỗi khi hủy tìm kiếm:', error);
            }
            
            // Quay về màn hình chính
            this.showMainInterface();
        });
        
        // Lấy số người đang tìm kiếm
        await this.updateSearchingCount();
        
        // Cập nhật số người đang tìm kiếm mỗi 5 giây
        this.searchingCountInterval = setInterval(async () => {
            await this.updateSearchingCount();
        }, 5000);
        
        // Kết nối WebSocket để nhận thông báo match
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.connectWebSocket();
        }
    }
    
    async showChatInterface() {
        // Dừng interval cập nhật số người đang tìm kiếm nếu có
        if (this.searchingCountInterval) {
            clearInterval(this.searchingCountInterval);
            this.searchingCountInterval = null;
        }
        
        // Tạo URL riêng cho phòng chat
        const chatUrl = `/chat/${this.currentConversation.conversation_id}`;
        window.history.pushState({ conversationId: this.currentConversation.conversation_id }, '', chatUrl);
        
        const container = document.querySelector('.container');
        container.innerHTML = `
            <div class="chat-container">
                <div class="chat-header">
                    <h3>Đã kết nối</h3>
                    <div class="chat-info">
                        <span class="chat-id">Phòng: #${this.currentConversation.conversation_id}</span>
                    </div>
                    <div class="chat-controls">
                        <button id="keepBtn" class="control-btn keep" title="Keep">❤️</button>
                        <button id="endBtn" class="control-btn" title="Kết thúc">❌</button>
                    </div>
                </div>
                
                <div class="chat-messages" id="chatMessages">
                    <div class="loading-messages" id="loadingMessages" style="text-align: center; padding: 20px; color: #666;">
                        <div>📱 Đang tải tin nhắn...</div>
                    </div>
                    <div class="typing-indicator" id="typingIndicator" style="display: none;">
                        Đối phương đang nhập...
                    </div>
                </div>
                
                <div class="chat-input">
                    <input type="text" id="messageInput" placeholder="Nhập tin nhắn..." maxlength="500">
                    <button id="sendBtn" class="send-btn">➤</button>
                </div>
            </div>
        `;
        
        // Load lịch sử tin nhắn
        await this.loadMessageHistory();
        
        this.connectWebSocket();
        this.setupChatEventListeners();
        
        // Bắt đầu countdown timer
        this.startCountdown();
    }
    
    async loadMessageHistory() {
        try {
            const response = await fetch(`/conversation/${this.currentConversation.conversation_id}/messages`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            if (response.ok) {
                const messages = await response.json();
                
                // Xóa loading indicator
                const loadingElement = document.getElementById('loadingMessages');
                if (loadingElement) {
                    loadingElement.remove();
                }
                
                // Hiển thị tin nhắn cũ
                if (messages.length > 0) {
                    console.log(`📚 Loaded ${messages.length} tin nhắn từ lịch sử`);
                    messages.forEach(message => {
                        this.addMessage(message);
                    });
                } else {
                    console.log('📚 Không có tin nhắn cũ');
                    // Hiển thị thông báo nếu không có tin nhắn
                    const chatMessages = document.getElementById('chatMessages');
                    const noMessagesDiv = document.createElement('div');
                    noMessagesDiv.style.cssText = 'text-align: center; padding: 20px; color: #666; font-style: italic;';
                    noMessagesDiv.textContent = 'Chưa có tin nhắn nào. Hãy bắt đầu cuộc trò chuyện! 💬';
                    chatMessages.appendChild(noMessagesDiv);
                }
            } else {
                console.error('❌ Lỗi khi load lịch sử tin nhắn:', response.status);
                // Xóa loading indicator và hiển thị lỗi
                const loadingElement = document.getElementById('loadingMessages');
                if (loadingElement) {
                    loadingElement.innerHTML = '<div style="color: #ff6b6b;">❌ Không thể tải tin nhắn</div>';
                }
            }
        } catch (error) {
            console.error('❌ Lỗi khi load lịch sử tin nhắn:', error);
            // Xóa loading indicator và hiển thị lỗi
            const loadingElement = document.getElementById('loadingMessages');
            if (loadingElement) {
                loadingElement.innerHTML = '<div style="color: #ff6b6b;">❌ Lỗi kết nối</div>';
            }
        }
    }
    
    connectWebSocket() {
        // Sử dụng URL động thay vì hardcode localhost
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            console.error('No access token available for WebSocket connection');
            return;
        }
        
        // Thêm token vào URL query parameter
        const wsUrl = `${protocol}//${host}/ws/${this.currentUser.id}?token=${encodeURIComponent(token)}`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('✅ WebSocket connected');
            // Reset reconnection attempts on successful connection
            this.reconnectionAttempts = 0;
        };
        
        this.websocket.onmessage = async (event) => {
            try {
                const data = JSON.parse(event.data);
                
                // Handle ping/pong để keep connection alive
                if (data.type === 'ping') {
                    this.websocket.send(JSON.stringify({ type: 'pong' }));
                    return;
                }
                
                await this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = (event) => {
            console.log('❌ WebSocket disconnected:', event.code, event.reason);
            
            // Handle authentication errors
            if (event.code === 4001) {
                console.error('WebSocket authentication failed:', event.reason);
                this.showError('Phiên đăng nhập đã hết hạn');
                setTimeout(() => {
                    this.handleLogout();
                }, 2000);
                return;
            }
            
            // Attempt reconnection for other errors
            if (event.code !== 1000) { // 1000 = normal closure
                this.attemptReconnection();
            }
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    attemptReconnection() {
        if (!this.reconnectionAttempts) {
            this.reconnectionAttempts = 0;
        }
        
        const maxAttempts = 5;
        const baseDelay = 1000; // 1 second
        
        if (this.reconnectionAttempts >= maxAttempts) {
            console.error('Max reconnection attempts reached');
            this.showError('Mất kết nối. Vui lòng tải lại trang.');
            return;
        }
        
        this.reconnectionAttempts++;
        const delay = baseDelay * Math.pow(2, this.reconnectionAttempts - 1); // Exponential backoff
        
        console.log(`Attempting WebSocket reconnection ${this.reconnectionAttempts}/${maxAttempts} in ${delay}ms`);
        
        setTimeout(() => {
            if (this.currentUser && this.currentUser.id) {
                this.connectWebSocket();
            }
        }, delay);
    }
    
    async handleWebSocketMessage(data) {
        try {
            const message = JSON.parse(data);
            console.log('📨 WebSocket message received:', message);
            
            switch (message.type) {
                case 'chat_message':
                    this.handleRealMessage(message.data);
                    break;
                case 'match_found':
                    await this.handleMatchFound(message.data);
                    break;
                case 'keep_status':
                    this.updateKeepStatus(message.data);
                    break;
                case 'typing_status':
                    this.showTypingIndicator(message.data.is_typing);
                    break;
                case 'conversation_ended':
                    this.handleConversationEnded(message.data);
                    break;
                case 'countdown_update':
                    this.handleCountdownUpdate(message.data);
                    break;
                default:
                    console.log('⚠️ Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
        }
    }
    
    handleCountdownUpdate(data) {
        console.log('🔄 Countdown update received:', data);
        
        // Cập nhật thông tin countdown từ server
        if (data.time_left !== undefined) {
            this.countdownTimeLeft = data.time_left;
        }
        if (data.start_time) {
            this.countdownStartTime = data.start_time;
        }
        if (data.both_kept !== undefined) {
            this.setBothKeptStatus(data.both_kept);
        }
        
        // Cập nhật hiển thị
        this.updateCountdownDisplay();
        
        // Nếu countdown đã hết thời gian và chưa keep, kết thúc
        if (data.expired && !this.bothKept) {
            console.log('❌ Countdown expired from server update');
            this.endCountdown();
        }
    }
    
    handleRealMessage(messageData) {
        // Nếu có tin nhắn tạm thời đang chờ và nội dung giống nhau, xóa tin nhắn tạm thời
        if (this.pendingTempMessage && 
            this.pendingTempMessage.content === messageData.content &&
            messageData.sender_id === this.currentUser.id) {
            
            // Xóa tin nhắn tạm thời
            const tempElement = document.querySelector(`[data-temp-id="${this.pendingTempMessage.id}"]`);
            if (tempElement) {
                tempElement.remove();
            }
            
            // Xóa reference
            this.pendingTempMessage = null;
        }
        
        // Thêm tin nhắn thật từ server
        this.addMessage(messageData);
    }
    
    async handleMatchFound(matchData) {
        console.log('🎯 Match found notification received:', matchData);
        
        // Lưu thông tin conversation
        this.currentConversation = matchData;
        
        // Hiển thị thông báo match thành công
        this.showSuccess(`Đã kết nối với ${matchData.matched_user?.nickname || 'người lạ'}! 🎉`);
        
        // Dừng interval cập nhật số người đang tìm kiếm nếu có
        if (this.searchingCountInterval) {
            clearInterval(this.searchingCountInterval);
            this.searchingCountInterval = null;
        }
        
        // Kiểm tra xem user có đang ở trang tìm kiếm không
        const isCurrentlySearching = document.querySelector('.searching-container') !== null;
        console.log('🔍 User currently searching:', isCurrentlySearching);
        
        // Chuyển sang chat interface ngay lập tức
        await this.showChatInterface();
        
        // Kết nối WebSocket nếu chưa kết nối
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.connectWebSocket();
        }
        
        // Cập nhật URL trong browser để có thể bookmark hoặc share
        if (matchData.chat_url) {
            window.history.pushState({ conversationId: matchData.conversation_id }, '', matchData.chat_url);
        }
        
        console.log('✅ Successfully switched to chat interface for match');
    }
    
    setupChatEventListeners() {
        const sendBtn = document.getElementById('sendBtn');
        const messageInput = document.getElementById('messageInput');
        const keepBtn = document.getElementById('keepBtn');
        const endBtn = document.getElementById('endBtn');
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        messageInput.addEventListener('input', () => this.handleTyping());
        
        keepBtn.addEventListener('click', () => this.toggleKeep());
        endBtn.addEventListener('click', () => this.endConversation());
    }
    
    addMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const isOwnMessage = message.sender_id === this.currentUser.id;
        
        const messageElement = document.createElement('div');
        messageElement.className = `message ${isOwnMessage ? 'sent' : 'received'}`;
        
        // Thêm data-temp-id nếu là tin nhắn tạm thời
        if (message.id && message.id > 1000000000000) { // ID tạm thời từ Date.now()
            messageElement.setAttribute('data-temp-id', message.id);
        }
        
        // Xử lý thời gian - chuyển đổi từ UTC sang múi giờ local
        let time;
        if (message.created_at) {
            const date = new Date(message.created_at);
            time = date.toLocaleTimeString('vi-VN', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Asia/Ho_Chi_Minh' // Đảm bảo sử dụng múi giờ Việt Nam
            });
        } else {
            time = new Date().toLocaleTimeString('vi-VN', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Asia/Ho_Chi_Minh'
            });
        }
        
        messageElement.innerHTML = `
            <div class="message-bubble">
                <div>${message.content}</div>
                <div class="message-time">${time}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    sendMessage() {
        const input = document.getElementById('messageInput');
        const content = input.value.trim();
        
        if (!content) return;
        
        // Hiển thị tin nhắn ngay lập tức cho user gửi
        const tempMessage = {
            id: Date.now(), // ID tạm thời
            conversation_id: this.currentConversation.conversation_id,
            sender_id: this.currentUser.id,
            content: content,
            message_type: 'text',
            created_at: new Date().toISOString()
        };
        
        this.addMessage(tempMessage);
        
        // Clear input ngay lập tức để UX tốt hơn
        input.value = '';
        
        // Lưu temp message để có thể xóa sau khi nhận được tin nhắn thật
        this.pendingTempMessage = tempMessage;
        
        // Gửi tin nhắn qua WebSocket với retry logic
        this.sendMessageWithRetry({
            type: 'chat_message',
            data: {
                conversation_id: this.currentConversation.conversation_id,
                content: content,
                message_type: 'text'
            }
        });
    }
    
    sendMessageWithRetry(message, retryCount = 0) {
        const maxRetries = 3;
        
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify(message));
            } catch (error) {
                console.error('Error sending message:', error);
                if (retryCount < maxRetries) {
                    setTimeout(() => {
                        this.sendMessageWithRetry(message, retryCount + 1);
                    }, 1000 * (retryCount + 1)); // Exponential backoff
                }
            }
        } else {
            if (retryCount < maxRetries) {
                setTimeout(() => {
                    this.sendMessageWithRetry(message, retryCount + 1);
                }, 1000 * (retryCount + 1));
            } else {
                this.showError('Không thể gửi tin nhắn. Vui lòng thử lại.');
            }
        }
    }
    
    handleTyping() {
        // Debounce typing events để tránh spam
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
        
        // Gửi typing status ngay lập tức
        const message = {
            type: 'typing',
            data: {
                conversation_id: this.currentConversation.conversation_id,
                is_typing: true
            }
        };
        
        this.sendMessageWithRetry(message);
        
        // Auto-stop typing sau 1 giây
        this.typingTimeout = setTimeout(() => {
            const stopTypingMessage = {
                type: 'typing',
                data: {
                    conversation_id: this.currentConversation.conversation_id,
                    is_typing: false
                }
            };
            this.sendMessageWithRetry(stopTypingMessage);
        }, 1000);
    }
    
    showTypingIndicator(isTyping) {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.style.display = isTyping ? 'block' : 'none';
        }
    }
    
    async toggleKeep() {
        try {
            const response = await fetch('/keep', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    conversation_id: this.currentConversation.conversation_id,
                    keep_status: !this.keepStatus
                })
            });
            
            if (response.ok) {
                this.keepStatus = !this.keepStatus;
                this.updateKeepStatus({ keep_status: this.keepStatus, both_kept: false });
            }
        } catch (error) {
            this.showError('Lỗi khi cập nhật Keep');
        }
    }
    
    updateKeepStatus(data) {
        const keepBtn = document.getElementById('keepBtn');
        if (data.both_kept) {
            keepBtn.innerHTML = '💖';
            this.setBothKeptStatus(true);
        } else if (data.keep_status) {
            keepBtn.innerHTML = '💗';
        } else {
            keepBtn.innerHTML = '❤️';
        }
    }
    
    async endConversation() {
        try {
            const response = await fetch('/end', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({
                    conversation_id: this.currentConversation.conversation_id
                })
            });
            
            if (response.ok) {
                // Khi người dùng chủ động kết thúc, cũng gọi handleConversationEnded
                // WebSocket sẽ gửi thông báo cho người còn lại
                this.handleConversationEnded({ redirect_url: '/' });
            }
        } catch (error) {
            this.showError('Lỗi khi kết thúc cuộc trò chuyện');
        }
    }
    
    handleConversationEnded(data = {}) {
        // Dừng countdown timer
        this.stopCountdown();
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        // Hiển thị thông báo phù hợp dựa trên lý do kết thúc
        if (data.reason === 'countdown_expired') {
            this.showError('Hết thời gian! Cuộc trò chuyện đã kết thúc.');
        } else {
            this.showSuccess('Cuộc trò chuyện đã kết thúc');
        }
        
        // Redirect về trang chủ hoặc URL được chỉ định
        setTimeout(() => {
            const redirectUrl = data.redirect_url || '/';
            window.location.href = redirectUrl;
        }, 2000);
    }
    
    async handleLogout() {
        try {
            await fetch('/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        // Dừng countdown timer
        this.stopCountdown();
        
        localStorage.removeItem('access_token');
        this.currentUser = null;
        this.currentConversation = null;
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        this.showLoginForm();
    }
    
    showError(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff6b6b;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
            z-index: 1000;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    showSuccess(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4CAF50;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    // Countdown timer methods
    startCountdown() {
        console.log('🚀 Starting countdown with:', {
            countdownStartTime: this.countdownStartTime,
            countdownTimeLeft: this.countdownTimeLeft,
            bothKept: this.bothKept
        });
        
        // Nếu đã có thông tin từ server, sử dụng thời gian từ server
        if (this.countdownStartTime) {
            this.countdownTimeLeft = this.calculateTimeLeftFromServer();
            console.log('📊 Using server time, calculated time left:', this.countdownTimeLeft);
        } else {
            // Nếu chưa có start time, sync với server trước
            console.log('📊 No start time available, syncing with server first');
            this.syncCountdownWithServer().then(() => {
                // Sau khi sync, tính toán lại thời gian
                if (this.countdownStartTime) {
                    this.countdownTimeLeft = this.calculateTimeLeftFromServer();
                    console.log('📊 After sync, calculated time left:', this.countdownTimeLeft);
                } else {
                    this.countdownTimeLeft = this.countdownDuration;
                    console.log('📊 Using default duration after sync:', this.countdownTimeLeft);
                }
                this.updateCountdownDisplay();
            });
            return; // Thoát sớm, sẽ tiếp tục sau khi sync
        }
        
        this.updateCountdownDisplay();
        
        // Clear interval cũ nếu có
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
        }
        if (this.serverSyncInterval) {
            clearInterval(this.serverSyncInterval);
        }
        
        this.countdownInterval = setInterval(() => {
            this.countdownTimeLeft--;
            this.updateCountdownDisplay();
            
            if (this.countdownTimeLeft <= 0) {
                this.endCountdown();
            }
        }, 1000);
        
        // Sync với server mỗi 15 giây để đảm bảo đồng bộ (giảm từ 30s xuống 15s)
        this.serverSyncInterval = setInterval(() => {
            this.syncCountdownWithServer();
        }, 15000);
        
        // Sync ngay lập tức sau 2 giây để đảm bảo đồng bộ ban đầu
        setTimeout(() => {
            this.syncCountdownWithServer();
        }, 2000);
    }
    
    calculateTimeLeftFromServer() {
        if (!this.countdownStartTime) {
            console.log('⚠️ No countdown start time available');
            return this.countdownDuration;
        }
        
        try {
            const startTime = new Date(this.countdownStartTime);
            const now = new Date();
            
            // Đảm bảo cả hai thời gian đều có timezone info
            if (startTime.toString() === 'Invalid Date') {
                console.error('❌ Invalid start time format:', this.countdownStartTime);
                return this.countdownDuration;
            }
            
            console.log('🕐 Time calculation:', {
                startTime: startTime.toISOString(),
                now: now.toISOString(),
                startTimeLocal: startTime.toString(),
                nowLocal: now.toString()
            });
            
            // Tính toán thời gian đã trôi qua (tính bằng milliseconds)
            const elapsed = Math.floor((now.getTime() - startTime.getTime()) / 1000);
            const timeLeft = this.countdownDuration - elapsed;
            
            console.log('⏱️ Time calculation result:', {
                elapsed: elapsed,
                timeLeft: timeLeft,
                duration: this.countdownDuration
            });
            
            return Math.max(0, timeLeft);
        } catch (error) {
            console.error('❌ Error calculating time left from server:', error);
            return this.countdownDuration;
        }
    }
    
    async syncCountdownWithServer() {
        if (!this.currentConversation) return;
        
        try {
            const response = await fetch(`/api/conversation/${this.currentConversation.conversation_id}/countdown`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                const serverTimeLeft = data.data.time_left;
                const serverExpired = data.data.expired;
                const serverBothKept = data.data.both_kept;
                const serverStartTime = data.data.start_time;
                
                console.log('🔄 Countdown sync with server:', {
                    serverTimeLeft: serverTimeLeft,
                    localTimeLeft: this.countdownTimeLeft,
                    serverExpired: serverExpired,
                    serverBothKept: serverBothKept,
                    serverStartTime: serverStartTime
                });
                
                // Cập nhật trạng thái keep
                this.setBothKeptStatus(serverBothKept);
                
                // Cập nhật start time nếu chưa có hoặc khác với server
                if (serverStartTime) {
                    if (!this.countdownStartTime || this.countdownStartTime !== serverStartTime) {
                        this.countdownStartTime = serverStartTime;
                        console.log('📊 Updated countdown start time from server');
                    }
                }
                
                // Nếu countdown đã hết thời gian và chưa keep, kết thúc ngay lập tức
                if (serverExpired && !this.bothKept) {
                    console.log('❌ Countdown expired on server, ending conversation immediately');
                    this.endCountdown();
                    return;
                }
                
                // Sync thời gian nếu chênh lệch > 3 giây (giảm từ 5s xuống 3s)
                if (Math.abs(this.countdownTimeLeft - serverTimeLeft) > 3) {
                    console.log(`🔄 Syncing countdown: local=${this.countdownTimeLeft}s, server=${serverTimeLeft}s`);
                    this.countdownTimeLeft = serverTimeLeft;
                    this.updateCountdownDisplay();
                }
                
                // Nếu thời gian còn lại <= 0, kết thúc ngay
                if (this.countdownTimeLeft <= 0 && !this.bothKept) {
                    console.log('❌ Countdown time left <= 0, ending conversation');
                    this.endCountdown();
                    return;
                }
            } else if (response.status === 404) {
                // Conversation không tồn tại, kết thúc
                console.log('❌ Conversation not found, ending');
                this.handleConversationEnded({ redirect_url: '/' });
            } else if (response.status === 401) {
                // Token hết hạn
                console.log('❌ Token expired during countdown sync');
                this.showError('Phiên đăng nhập đã hết hạn');
                setTimeout(() => {
                    this.handleLogout();
                }, 2000);
            }
        } catch (error) {
            console.error('❌ Error syncing countdown with server:', error);
            // Không làm gì nếu có lỗi network, tiếp tục với countdown local
        }
    }
    
    stopCountdown() {
        if (this.countdownInterval) {
            clearInterval(this.countdownInterval);
            this.countdownInterval = null;
        }
        if (this.serverSyncInterval) {
            clearInterval(this.serverSyncInterval);
            this.serverSyncInterval = null;
        }
    }
    
    updateCountdownDisplay() {
        const headerElement = document.querySelector('.chat-header h3');
        if (!headerElement) return;
        
        if (this.bothKept) {
            // Nếu cả 2 đã keep, hiển thị "Đã kết nối"
            headerElement.textContent = 'Đã kết nối';
            headerElement.style.color = '#4CAF50';
            headerElement.className = ''; // Xóa tất cả class countdown
        } else {
            // Hiển thị countdown
            const minutes = Math.floor(this.countdownTimeLeft / 60);
            const seconds = this.countdownTimeLeft % 60;
            const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            headerElement.textContent = `⏰ ${timeString}`;
            headerElement.className = 'countdown'; // Thêm class countdown
            
            // Đổi màu và animation khi gần hết thời gian
            if (this.countdownTimeLeft <= 30) {
                headerElement.style.color = '#ff6b6b'; // Đỏ khi còn 30s
                headerElement.classList.add('danger');
                headerElement.classList.remove('warning');
            } else if (this.countdownTimeLeft <= 60) {
                headerElement.style.color = '#ffa726'; // Cam khi còn 1 phút
                headerElement.classList.add('warning');
                headerElement.classList.remove('danger');
            } else {
                headerElement.style.color = '#2196F3'; // Xanh dương
                headerElement.classList.remove('warning', 'danger');
            }
        }
    }
    
    endCountdown() {
        this.stopCountdown();
        this.showError('Hết thời gian! Cuộc trò chuyện sẽ kết thúc.');
        
        // Kết thúc conversation ngay lập tức khi countdown hết
        this.endConversation();
    }
    
    setBothKeptStatus(bothKept) {
        this.bothKept = bothKept;
        if (bothKept) {
            this.stopCountdown();
            this.updateCountdownDisplay();
        }
    }
    
    async updateSearchingCount() {
        try {
            const response = await fetch('/api/searching-count');
            if (response.ok) {
                const data = await response.json();
                const countElement = document.getElementById('searchingCount');
                if (countElement) {
                    countElement.textContent = data.data.searching_count;
                }
            }
        } catch (error) {
            console.error('Lỗi khi cập nhật số người đang tìm kiếm:', error);
            const countElement = document.getElementById('searchingCount');
            if (countElement) {
                countElement.textContent = '?';
            }
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MapmoApp();
}); 