import os
import uuid
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def generate_unique_id():
    """Generate a unique ID for requests."""
    return str(uuid.uuid4())

def get_timestamp():
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()

def safe_delete_file(file_path):
    """Safely delete a file if it exists."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False
    return False