from celery import Celery
import os
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

celery_app = Celery(
    'image_processing',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Optional configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Import and register task directly
from app.tasks.worker import process_images_task
celery_app.task(name='process_images_task')(process_images_task)

if __name__ == '__main__':
    celery_app.start()