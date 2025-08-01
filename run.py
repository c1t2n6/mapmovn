#!/usr/bin/env python3
"""
Mapmo.vn - Anonymous Web Chat Application
Script để chạy ứng dụng
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print("🚀 Starting Mapmo.vn - Anonymous Web Chat")
    print(f"📍 Server will run on http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    ) 