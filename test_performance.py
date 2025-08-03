#!/usr/bin/env python3
"""
Performance test script for Mapmo.vn chat synchronization
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

class PerformanceTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    async def test_websocket_connection(self, user_id, token):
        """Test WebSocket connection performance"""
        start_time = time.time()
        
        try:
            # Connect WebSocket
            ws_url = f"{self.base_url.replace('http', 'ws')}/ws/{user_id}?token={token}"
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    connect_time = time.time() - start_time
                    
                    # Send test message
                    message = {
                        "type": "chat_message",
                        "data": {
                            "conversation_id": 1,
                            "content": "Test message",
                            "message_type": "text"
                        }
                    }
                    
                    send_start = time.time()
                    await ws.send_str(json.dumps(message))
                    send_time = time.time() - send_start
                    
                    # Wait for response
                    response_start = time.time()
                    response = await asyncio.wait_for(ws.receive(), timeout=5.0)
                    response_time = time.time() - response_start
                    
                    return {
                        "connect_time": connect_time,
                        "send_time": send_time,
                        "response_time": response_time,
                        "total_time": time.time() - start_time,
                        "success": True
                    }
                    
        except Exception as e:
            return {
                "connect_time": time.time() - start_time,
                "send_time": 0,
                "response_time": 0,
                "total_time": time.time() - start_time,
                "success": False,
                "error": str(e)
            }
    
    async def test_api_endpoint(self, endpoint, method="GET", data=None, headers=None):
        """Test API endpoint performance"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                        response_time = time.time() - start_time
                        return {
                            "endpoint": endpoint,
                            "method": method,
                            "response_time": response_time,
                            "status_code": response.status,
                            "success": response.status < 400
                        }
                elif method == "POST":
                    async with session.post(f"{self.base_url}{endpoint}", json=data, headers=headers) as response:
                        response_time = time.time() - start_time
                        return {
                            "endpoint": endpoint,
                            "method": method,
                            "response_time": response_time,
                            "status_code": response.status,
                            "success": response.status < 400
                        }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "response_time": time.time() - start_time,
                "status_code": 0,
                "success": False,
                "error": str(e)
            }
    
    async def run_performance_tests(self):
        """Run all performance tests"""
        print("🚀 Starting performance tests...")
        print("=" * 50)
        
        # Test API endpoints
        print("📡 Testing API endpoints...")
        
        # Test health check
        health_result = await self.test_api_endpoint("/health")
        self.results.append(health_result)
        print(f"Health check: {health_result['response_time']:.3f}s")
        
        # Test searching count
        search_result = await self.test_api_endpoint("/api/searching-count")
        self.results.append(search_result)
        print(f"Searching count: {search_result['response_time']:.3f}s")
        
        # Test WebSocket (if we have test users)
        print("\n🔌 Testing WebSocket performance...")
        try:
            # Try to login with test user
            login_data = {
                "username": "user1",
                "password": "password"
            }
            
            login_result = await self.test_api_endpoint("/login", method="POST", data=login_data)
            if login_result['success']:
                print(f"Login: {login_result['response_time']:.3f}s")
                
                # Test WebSocket connection
                # Note: This is a simplified test - in real scenario you'd need proper authentication
                print("WebSocket test requires proper authentication setup")
            else:
                print("Login failed, skipping WebSocket test")
                
        except Exception as e:
            print(f"WebSocket test error: {e}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Performance Test Summary")
        print("=" * 50)
        
        successful_tests = [r for r in self.results if r['success']]
        failed_tests = [r for r in self.results if not r['success']]
        
        if successful_tests:
            avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
            max_response_time = max(r['response_time'] for r in successful_tests)
            min_response_time = min(r['response_time'] for r in successful_tests)
            
            print(f"✅ Successful tests: {len(successful_tests)}")
            print(f"❌ Failed tests: {len(failed_tests)}")
            print(f"📈 Average response time: {avg_response_time:.3f}s")
            print(f"📈 Max response time: {max_response_time:.3f}s")
            print(f"📈 Min response time: {min_response_time:.3f}s")
            
            # Performance recommendations
            print("\n💡 Performance Recommendations:")
            if avg_response_time > 1.0:
                print("⚠️  Average response time is high (>1s). Consider:")
                print("   - Database query optimization")
                print("   - Connection pooling")
                print("   - Caching frequently accessed data")
            elif avg_response_time > 0.5:
                print("⚠️  Response time is moderate (>0.5s). Consider:")
                print("   - Async processing for heavy operations")
                print("   - Database indexing")
            else:
                print("✅ Response times are good!")
                
        if failed_tests:
            print(f"\n❌ Failed tests:")
            for test in failed_tests:
                print(f"   - {test['endpoint']}: {test.get('error', 'Unknown error')}")

async def main():
    """Main function to run performance tests"""
    test = PerformanceTest()
    await test.run_performance_tests()

if __name__ == "__main__":
    asyncio.run(main()) 