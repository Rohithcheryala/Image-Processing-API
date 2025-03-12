import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'image_processing.db')}"

# Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Webhook (if configured)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# Compression quality for processed images (0-100)
IMAGE_COMPRESSION_QUALITY = 50

# Add this to your existing config.py
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")  # Default to localhost for development