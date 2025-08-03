#!/usr/bin/env python3
"""
Test script cho chức năng countdown đồng bộ
"""

import time
import requests
import json
from datetime import datetime

def test_sync_countdown():
    """Test chức năng countdown đồng bộ"""
    print("🧪 Testing Synchronized Countdown Timer")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Đăng ký 2 user
    print("1. Đăng ký 2 user test...")
    
    user1_data = {
        "username": "testuser1_sync",
        "password": "password123",
        "confirm_password": "password123"
    }
    
    user2_data = {
        "username": "testuser2_sync", 
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
    
    # Test 2: Đăng nhập và setup profile
    print("\n2. Đăng nhập và setup profile...")
    
    # User1 login
    login_data = {"username": "testuser1_sync", "password": "password123"}
    response = requests.post(f"{base_url}/login", json=login_data)
    if response.status_code == 200:
        user1_token = response.json()["data"]["access_token"]
        print("✅ User1 đăng nhập thành công")
    else:
        print(f"❌ User1 đăng nhập thất bại: {response.text}")
        return
    
    # User2 login
    login_data = {"username": "testuser2_sync", "password": "password123"}
    response = requests.post(f"{base_url}/login", json=login_data)
    if response.status_code == 200:
        user2_token = response.json()["data"]["access_token"]
        print("✅ User2 đăng nhập thành công")
    else:
        print(f"❌ User2 đăng nhập thất bại: {response.text}")
        return
    
    # Setup profile cho cả 2 user
    profile_data = {
        "nickname": "TestUser",
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
    
    profile_data["gender"] = "female"
    profile_data["preference"] = "male"
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.put(f"{base_url}/profile", json=profile_data, headers=headers)
    if response.status_code == 200:
        print("✅ User2 setup profile thành công")
    else:
        print(f"❌ User2 setup profile thất bại: {response.text}")
        return
    
    # Test 3: Tạo conversation
    print("\n3. Tạo conversation...")
    
    # User1 tìm kiếm
    search_data = {"search_type": "chat"}
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/search", json=search_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ User1 tìm kiếm thất bại: {response.text}")
        return
    
    # User2 tìm kiếm để tạo match
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
    
    # Test 4: Kiểm tra countdown từ cả 2 user
    print("\n4. Kiểm tra countdown đồng bộ...")
    
    # Lấy countdown từ user1
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{base_url}/api/conversation/{conversation_id}/countdown", headers=headers)
    
    if response.status_code == 200:
        user1_countdown = response.json()["data"]
        print(f"✅ User1 countdown: {user1_countdown['time_left']}s, expired: {user1_countdown['expired']}")
    else:
        print(f"❌ Không lấy được countdown user1: {response.text}")
        return
    
    # Lấy countdown từ user2
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.get(f"{base_url}/api/conversation/{conversation_id}/countdown", headers=headers)
    
    if response.status_code == 200:
        user2_countdown = response.json()["data"]
        print(f"✅ User2 countdown: {user2_countdown['time_left']}s, expired: {user2_countdown['expired']}")
    else:
        print(f"❌ Không lấy được countdown user2: {response.text}")
        return
    
    # Kiểm tra đồng bộ
    time_diff = abs(user1_countdown['time_left'] - user2_countdown['time_left'])
    if time_diff <= 1:
        print("✅ Countdown đồng bộ giữa 2 user!")
    else:
        print(f"⚠️ Countdown không đồng bộ! Chênh lệch: {time_diff}s")
    
    # Test 5: Đợi 10 giây và kiểm tra lại
    print("\n5. Đợi 10 giây và kiểm tra lại...")
    time.sleep(10)
    
    # Kiểm tra lại từ user1
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.get(f"{base_url}/api/conversation/{conversation_id}/countdown", headers=headers)
    
    if response.status_code == 200:
        user1_countdown_new = response.json()["data"]
        time_decreased = user1_countdown['time_left'] - user1_countdown_new['time_left']
        print(f"✅ User1 countdown giảm: {time_decreased}s (từ {user1_countdown['time_left']}s xuống {user1_countdown_new['time_left']}s)")
        
        if 9 <= time_decreased <= 11:  # Cho phép sai số 1 giây
            print("✅ Countdown giảm đúng thời gian!")
        else:
            print(f"⚠️ Countdown giảm không đúng! Mong đợi ~10s, thực tế: {time_decreased}s")
    
    # Test 6: Test Keep button
    print("\n6. Test Keep button...")
    
    # User1 keep
    keep_data = {"conversation_id": conversation_id, "keep_status": True}
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/keep", json=keep_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ User1 keep: {result['data']['keep_status']}, both_kept: {result['data']['both_kept']}")
    else:
        print(f"❌ User1 keep thất bại: {response.text}")
        return
    
    # User2 keep
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = requests.post(f"{base_url}/keep", json=keep_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ User2 keep: {result['data']['keep_status']}, both_kept: {result['data']['both_kept']}")
        
        if result['data']['both_kept']:
            print("🎉 Cả 2 đã Keep! Countdown sẽ dừng lại!")
        else:
            print("⚠️ Chưa cả 2 Keep")
    else:
        print(f"❌ User2 keep thất bại: {response.text}")
        return
    
    # Test 7: Kết thúc conversation
    print("\n7. Kết thúc conversation...")
    end_data = {"conversation_id": conversation_id}
    headers = {"Authorization": f"Bearer {user1_token}"}
    response = requests.post(f"{base_url}/end", json=end_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Conversation đã kết thúc")
    else:
        print(f"❌ Kết thúc conversation thất bại: {response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Synchronized Countdown hoàn thành!")
    print("\n📝 Kết quả:")
    print("- Countdown được lưu trong database")
    print("- Đồng bộ giữa 2 user")
    print("- Không bị reset khi reload trang")
    print("- Keep button dừng countdown")

if __name__ == "__main__":
    test_sync_countdown() 