#!/usr/bin/env python3
"""
Migration script để thêm cột countdown_start_time vào bảng conversations
"""

import sqlite3
from datetime import datetime, timezone

def migrate_countdown_column():
    """Thêm cột countdown_start_time vào bảng conversations"""
    print("🔄 Starting migration: Add countdown_start_time column")
    
    try:
        # Kết nối database
        conn = sqlite3.connect('mapmo.db')
        cursor = conn.cursor()
        
        # Kiểm tra xem cột đã tồn tại chưa
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'countdown_start_time' in columns:
            print("✅ Column countdown_start_time already exists")
            return
        
        # Thêm cột countdown_start_time
        print("📝 Adding countdown_start_time column...")
        cursor.execute("""
            ALTER TABLE conversations 
            ADD COLUMN countdown_start_time DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        
        # Cập nhật các conversation hiện tại với thời gian bắt đầu
        print("🔄 Updating existing conversations...")
        cursor.execute("""
            UPDATE conversations 
            SET countdown_start_time = created_at 
            WHERE countdown_start_time IS NULL
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Kiểm tra kết quả
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        print(f"📊 Total conversations: {count}")
        
        cursor.execute("SELECT id, created_at, countdown_start_time FROM conversations LIMIT 3")
        sample_data = cursor.fetchall()
        print("📋 Sample data:")
        for row in sample_data:
            print(f"   Conversation {row[0]}: created={row[1]}, countdown_start={row[2]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_countdown_column() 