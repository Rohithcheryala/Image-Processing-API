# Image Processing API

A FastAPI-based service for processing product images from CSV files. This service allows users to upload CSV files containing product information and image URLs, processes the images asynchronously, and provides status tracking and webhook notifications.

## Features

- CSV file upload and validation
- Asynchronous image processing
- Image compression and optimization
- Real-time status tracking
- Webhook notifications for process completion
- RESTful API endpoints
- Detailed error handling
- Progress monitoring
- Downloadable results

## Tech Stack

- **Framework**: FastAPI
- **Task Queue**: Celery with Redis
- **Database**: SQLite with SQLAlchemy
- **Image Processing**: Pillow (PIL)
- **Async HTTP**: httpx
- **File Handling**: Pandas
- **Development Server**: Uvicorn

## Prerequisites

- Python 3.8+
- Redis Server
- Virtual Environment (recommended)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/image-processing-api.git
cd image-processing-api
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up Redis:

```bash
# On Ubuntu/Debian
sudo apt-get install redis-server
# On macOS
brew install redis
# On Windows
# Download and install from https://github.com/microsoftarchive/redis/releases
```

## Running the Application

1. Start redis-server

```bash
redis-server
```

2. Start the FastAPI server:

```bash
python -m app.main
```

3. Start Celery worker:

```bash
celery -A celery_app worker --loglevel=info
```

## API Endpoints

### Upload CSV

- **URL**: `/api/upload`
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `file`: CSV file
  - `webhook_url`: Optional webhook URL for notifications, visit https://webhook.site/#!/

### Check Status

- **URL**: `/api/status/{request_id}`
- **Method**: GET
- **Response**: Processing status and progress

### Get Details

- **URL**: `/api/details/{request_id}`
- **Method**: GET
- **Response**: Detailed processing information

### Download Results

- **URL**: `/api/download/{request_id}`
- **Method**: GET
- **Response**: Processed CSV file

### Get Processed Image

- **URL**: `/api/image/{filename}`
- **Method**: GET
- **Response**: Processed image file

## CSV File Format

Required columns:

- S. No. (Serial Number)
- Product Name
- Input Image Urls (comma-separated URLs)

Example:

```
S. No.,Product Name,Input Image Urls
1,SKU1,https://example.com/image1.jpg,https://example.com/image2.jpg
2,SKU2,https://example.com/image3.jpg
```

## Error Handling

The API provides detailed error messages for:

- Invalid CSV format
- Missing required columns
- Invalid image URLs
- Processing failures
- Server errors

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Postman Collection

Not able to include public accessible postman collection link as it requires enterprise plan.

For testing please use Swagger UI: http://localhost:8000/docs

## Directory Structure

```
/
├── app/                      # Main application package
│   ├── __init__.py          # Package initializer
│   ├── config.py            # Configuration settings
│   ├── api/                 # API endpoints and routing
│   │   ├── __init__.py
│   │   └── endpoints.py     # API route definitions
│   ├── database/            # Database related code
│   │   ├── __init__.py
│   │   └── db.py           # Database models and connection
│   ├── models/             # Data models and schemas
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models/schemas
│   ├── services/           # Business logic services
│   │   ├── __init__.py
│   │   ├── csv_service.py  # CSV processing logic
│   │   └── image_service.py # Image processing logic
│   ├── tasks/              # Async task definitions
│   │   ├── __init__.py
│   │   └── worker.py       # Celery worker tasks
│   └── utils/              # Utility functions
│       ├── __init__.py
│       └── helpers.py      # Helper functions
├── data/                   # Data storage directory
│   ├── uploads/           # For uploaded CSV files
│   └── processed/         # For processed images
├── celery_app.py          # Celery configuration
├── image_processing.db    # SQLite database file
└── requirements.txt       # Project dependencies
```
