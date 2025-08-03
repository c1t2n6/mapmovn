#!/usr/bin/env python3
"""
Test script cho chức năng countdown timer
"""

import time
import requests
import json
from datetime import datetime

def test_countdown_timer():
    """Test chức năng countdown timer"""
    print("🧪 Testing Countdown Timer Functionality")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Đăng ký 2 user
    print("1. Đăng ký 2 user test...")
    
    user1_data = {
        "username": "testuser1_countdown",
        "password": "password123",
        "confirm_password": "password123"
    }
    
    user2_data = {
        "username": "testuser2_countdown", 
        "password": "password123",
        "confirm_password": "password123"
    }
    
    # Đăng ký user1
    response = requests.post(f"{base_url}/register", json=user1_data)
    if response.status_code == 200:
        print("✅ User1 đăng ký thành công")
    else:
        print(f"❌ User1 đăng ký thất bại: {response.text}")
        return
    
    # Đăng ký user2
    response = requests.post(f"{base_url}/register", json=user2_data)
    if response.status_code == 200:
        print("✅ User2 đăng ký thành công")
    else:
        print(f"❌ User2 đăng ký thất bại: {response.text}")
        return
    
    # Test 2: Đăng nhập user1
    print("\n2. Đăng nhập user1...")
    login_data = {
        "username": "testuser1_countdown",
        "password": "password123"
    }
    
    response = requests.post(f"{base_url}/login", json=login_data)
    if response.status_code == 200:
        user1_token = response.json()["data"]["access_token"]
        print("✅ User1 đăng nhập thành công")
    else:
        print(f"❌ User1 đăng nhập thất bại: {response.text}")
        return
    
    # Test 3: Setup profile cho user1
    print("\n3. Setup profile cho user1...")
    profile_data = {
        "nickname": "TestUser1",
        "dob": "1990-01-01",
        "gender": "male",
        "preference": "female",
        "goal": "Kết bạn mới thôi 🥰",
        "interests": ["Tập gym 💪", "Chụp ảnh 📷"]
    }
    
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.put(f"{base_url}/profile", json=profile_data, headers=headers)
    if response.status_code == 200:
        print("✅ User1 setup profile thành công")
    else:
        print(f"❌ User1 setup profile thất bại: {response.text}")
        return
    
    # Test 4: Đăng nhập user2
    print("\n4. Đăng nhập user2...")
    login_data = {
        "username": "testuser2_countdown",
        "password": "password123"
    }
    
    response = requests.post(f"{base_url}/login", json=login_data)
    if response.status_code == 200:
        user2_token = response.json()["data"]["access_token"]
        print("✅ User2 đăng nhập thành công")
    else:
        print(f"❌ User2 đăng nhập thất bại: {response.text}")
        return
    
    # Test 5: Setup profile cho user2
    print("\n5. Setup profile cho user2...")
    profile_data = {
        "nickname": "TestUser2",
        "dob": "1992-01-01",
        "gender": "female",
        "preference": "male",
        "goal": "Kết bạn mới thôi 🥰",
        "interests": ["Chụp ảnh 📷", "Du lịch ✈️"]
    }
    
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.put(f"{base_url}/profile", json=profile_data, headers=headers)
    if response.status_code == 200:
        print("✅ User2 setup profile thành công")
    else:
        print(f"❌ User2 setup profile thất bại: {response.text}")
        return
    
    # Test 6: Bắt đầu tìm kiếm với user1
    print("\n6. User1 bắt đầu tìm kiếm...")
    search_data = {"search_type": "chat"}
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/search", json=search_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if result["data"].get("status") == "searching":
            print("✅ User1 đang tìm kiếm...")
        else:
            print("✅ User1 đã tìm thấy match!")
            conversation_id = result["data"]["conversation_id"]
    else:
        print(f"❌ User1 tìm kiếm thất bại: {response.text}")
        return
    
    # Test 7: Bắt đầu tìm kiếm với user2 để tạo match
    print("\n7. User2 bắt đầu tìm kiếm để tạo match...")
    search_data = {"search_type": "chat"}
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.post(f"{base_url}/search", json=search_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        if "conversation_id" in result["data"]:
            conversation_id = result["data"]["conversation_id"]
            print(f"✅ Match thành công! Conversation ID: {conversation_id}")
        else:
            print("❌ Không tạo được match")
            return
    else:
        print(f"❌ User2 tìm kiếm thất bại: {response.text}")
        return
    
    # Test 8: Kiểm tra thông tin conversation
    print("\n8. Kiểm tra thông tin conversation...")
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{base_url}/api/conversation/{conversation_id}", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Lấy thông tin conversation thành công")
        print(f"   - Conversation ID: {result['data']['conversation_id']}")
        print(f"   - Type: {result['data']['conversation_type']}")
        print(f"   - Matched user: {result['data']['matched_user']['nickname']}")
        print(f"   - Keep status: {result['data']['keep_status']}")
    else:
        print(f"❌ Lấy thông tin conversation thất bại: {response.text}")
        return
    
    # Test 9: Test Keep button
    print("\n9. Test Keep button...")
    keep_data = {
        "conversation_id": conversation_id,
        "keep_status": True
    }
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/keep", json=keep_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ User1 đã nhấn Keep")
        print(f"   - Keep status: {result['data']['keep_status']}")
        print(f"   - Both kept: {result['data']['both_kept']}")
    else:
        print(f"❌ Keep thất bại: {response.text}")
        return
    
    # Test 10: User2 cũng nhấn Keep
    print("\n10. User2 cũng nhấn Keep...")
    keep_data = {
        "conversation_id": conversation_id,
        "keep_status": True
    }
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.post(f"{base_url}/keep", json=keep_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ User2 đã nhấn Keep")
        print(f"   - Keep status: {result['data']['keep_status']}")
        print(f"   - Both kept: {result['data']['both_kept']}")
        
        if result['data']['both_kept']:
            print("🎉 Cả 2 đã Keep! Countdown sẽ dừng lại!")
        else:
            print("⚠️ Chưa cả 2 Keep")
    else:
        print(f"❌ Keep thất bại: {response.text}")
        return
    
    # Test 11: Kết thúc conversation
    print("\n11. Kết thúc conversation...")
    end_data = {"conversation_id": conversation_id}
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/end", json=end_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Conversation đã kết thúc")
    else:
        print(f"❌ Kết thúc conversation thất bại: {response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Countdown Timer hoàn thành!")
    print("\n📝 Hướng dẫn test trên frontend:")
    print("1. Mở 2 tab browser khác nhau")
    print("2. Đăng nhập với 2 user test")
    print("3. Vào chat room và quan sát countdown timer")
    print("4. Nhấn Keep button và xem countdown có dừng không")
    print("5. Đợi 5 phút để xem countdown có tự động kết thúc không")

if __name__ == "__main__":
    test_countdown_timer() 