import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mapmo.db")
    
    # WebSocket settings
    WEBSOCKET_PING_INTERVAL = 30  # seconds
    WEBSOCKET_PING_TIMEOUT = 10   # seconds
    WEBSOCKET_MAX_CONNECTIONS = 1000
    
    # Message processing settings
    MESSAGE_BATCH_SIZE = 10
    MESSAGE_PROCESSING_INTERVAL = 0.1  # seconds
    TYPING_DEBOUNCE_DELAY = 1.0  # seconds
    
    # Cache settings
    CONVERSATION_CACHE_TTL = 300  # 5 minutes
    USER_CACHE_TTL = 600  # 10 minutes
    
    # Performance settings
    MAX_MESSAGES_PER_CONVERSATION = 1000
    CLEANUP_INTERVAL = 30  # seconds
    
    # Security settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # Logging settings
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_SQL_LOGGING = os.getenv("ENABLE_SQL_LOGGING", "false").lower() == "true"

settings = Settings() 