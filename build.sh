#!/bin/bash
# Build script for Render deployment

echo "🚀 Starting build process..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create database if it doesn't exist
echo "🗄️ Setting up database..."
python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('Database setup completed')
"

echo "✅ Build completed successfully!" 