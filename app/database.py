from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings

# Tối ưu hóa engine với connection pooling và các cấu hình hiệu suất
if "sqlite" in settings.DATABASE_URL:
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections every hour
        echo=settings.ENABLE_SQL_LOGGING  # Set to True for SQL debugging
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.ENABLE_SQL_LOGGING
    )

# Tối ưu hóa session với các cấu hình hiệu suất
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Prevent lazy loading issues
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 