#!/usr/bin/env python3
"""
Test script để kiểm tra countdown synchronization
Chạy: python test_countdown_sync.py
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

class CountdownSyncTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.session = None
        self.user1_token = None
        self.user2_token = None
        self.conversation_id = None
        
    async def setup(self):
        """Thiết lập test environment"""
        self.session = aiohttp.ClientSession()
        
        # Login 2 users
        await self.login_users()
        
        # Tạo conversation
        await self.create_conversation()
        
    async def login_users(self):
        """Login 2 users để test"""
        # Login user1
        login_data1 = {
            "username": "user1",
            "password": "password"
        }
        
        async with self.session.post(f"{self.base_url}/login", json=login_data1) as response:
            if response.status == 200:
                data = await response.json()
                self.user1_token = data.get("access_token")
                print(f"✅ User1 logged in: {data.get('message')}")
            else:
                print(f"❌ User1 login failed: {response.status}")
                
        # Login user2
        login_data2 = {
            "username": "user2", 
            "password": "password"
        }
        
        async with self.session.post(f"{self.base_url}/login", json=login_data2) as response:
            if response.status == 200:
                data = await response.json()
                self.user2_token = data.get("access_token")
                print(f"✅ User2 logged in: {data.get('message')}")
            else:
                print(f"❌ User2 login failed: {response.status}")
    
    async def create_conversation(self):
        """Tạo conversation giữa 2 users"""
        # Start search cho user1
        search_data = {
            "search_type": "chat"
        }
        
        headers1 = {"Authorization": f"Bearer {self.user1_token}"}
        async with self.session.post(f"{self.base_url}/search", json=search_data, headers=headers1) as response:
            if response.status == 200:
                print("✅ User1 started search")
            else:
                print(f"❌ User1 search failed: {response.status}")
        
        # Start search cho user2
        headers2 = {"Authorization": f"Bearer {self.user2_token}"}
        async with self.session.post(f"{self.base_url}/search", json=search_data, headers=headers2) as response:
            if response.status == 200:
                print("✅ User2 started search")
            else:
                print(f"❌ User2 search failed: {response.status}")
        
        # Đợi một chút để matching xảy ra
        await asyncio.sleep(2)
        
        # Kiểm tra conversation được tạo
        await self.check_conversation()
    
    async def check_conversation(self):
        """Kiểm tra conversation đã được tạo"""
        # Kiểm tra từ user1
        headers1 = {"Authorization": f"Bearer {self.user1_token}"}
        async with self.session.get(f"{self.base_url}/api/me", headers=headers1) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("data", {}).get("current_conversation"):
                    self.conversation_id = data["data"]["current_conversation"]["conversation_id"]
                    print(f"✅ Conversation created: {self.conversation_id}")
                else:
                    print("❌ No conversation found for user1")
            else:
                print(f"❌ Failed to get user1 info: {response.status}")
    
    async def test_countdown_sync(self):
        """Test countdown synchronization"""
        if not self.conversation_id:
            print("❌ No conversation to test")
            return
            
        print(f"\n🔄 Testing countdown sync for conversation {self.conversation_id}")
        
        # Test countdown sync trong 30 giây
        start_time = time.time()
        test_duration = 30
        
        while time.time() - start_time < test_duration:
            # Lấy countdown status từ user1
            headers1 = {"Authorization": f"Bearer {self.user1_token}"}
            async with self.session.get(f"{self.base_url}/api/conversation/{self.conversation_id}/countdown", headers=headers1) as response1:
                if response1.status == 200:
                    data1 = await response1.json()
                    time_left1 = data1["data"]["time_left"]
                    expired1 = data1["data"]["expired"]
                    both_kept1 = data1["data"]["both_kept"]
                else:
                    print(f"❌ Failed to get countdown for user1: {response1.status}")
                    continue
            
            # Lấy countdown status từ user2
            headers2 = {"Authorization": f"Bearer {self.user2_token}"}
            async with self.session.get(f"{self.base_url}/api/conversation/{self.conversation_id}/countdown", headers=headers2) as response2:
                if response2.status == 200:
                    data2 = await response2.json()
                    time_left2 = data2["data"]["time_left"]
                    expired2 = data2["data"]["expired"]
                    both_kept2 = data2["data"]["both_kept"]
                else:
                    print(f"❌ Failed to get countdown for user2: {response2.status}")
                    continue
            
            # Kiểm tra synchronization
            time_diff = abs(time_left1 - time_left2)
            expired_diff = expired1 != expired2
            both_kept_diff = both_kept1 != both_kept2
            
            elapsed = time.time() - start_time
            
            print(f"⏱️  [{elapsed:.1f}s] User1: {time_left1}s, User2: {time_left2}s, Diff: {time_diff}s")
            
            if time_diff > 3:
                print(f"⚠️  WARNING: Time difference > 3s: {time_diff}s")
            
            if expired_diff:
                print(f"⚠️  WARNING: Expired status mismatch: User1={expired1}, User2={expired2}")
            
            if both_kept_diff:
                print(f"⚠️  WARNING: Both kept status mismatch: User1={both_kept1}, User2={both_kept2}")
            
            # Đợi 2 giây trước khi test tiếp
            await asyncio.sleep(2)
        
        print(f"\n✅ Countdown sync test completed after {test_duration}s")
    
    async def cleanup(self):
        """Dọn dẹp sau khi test"""
        if self.session:
            await self.session.close()
    
    async def run_test(self):
        """Chạy toàn bộ test"""
        try:
            await self.setup()
            await self.test_countdown_sync()
        finally:
            await self.cleanup()

async def main():
    """Main function"""
    print("🚀 Starting countdown synchronization test...")
    test = CountdownSyncTest()
    await test.run_test()
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 