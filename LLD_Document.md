# Low-Level Design Document: Image Processing System

## 1. System Overview

This document provides a detailed technical design for an asynchronous image processing system. The system accepts CSV files containing product information and image URLs, processes the images by compressing them to 50% quality, and stores the processed images alongside their original product information. Users can track the status of their processing requests and download the results when complete.

## 2. System Architecture

The architecture follows a microservices approach with asynchronous processing capabilities using Python, FastAPI, Celery, and SQLite.

### 2.1 High-Level Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  FastAPI    │────▶│   Celery    │
│  (Upload    │     │   Server    │     │   Worker    │
│   CSV)      │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   SQLite    │     │  File System│
                    │  Database   │     │  (Processed │
                    │             │     │   Images)   │
                    └─────────────┘     └─────────────┘
                           │                   │
                           └───────────────────┘
                                   │
                                   ▼
                           ┌─────────────┐
                           │   Webhook   │
                           │ Notification│
                           │  (Optional) │
                           └─────────────┘
```

## 3. Component Description

### 3.1 API Server (FastAPI)

The API server handles HTTP requests from clients, manages file uploads, and initiates asynchronous processing tasks.

#### Key Responsibilities:
- Accept and validate CSV file uploads
- Generate unique request IDs
- Queue image processing tasks
- Provide status updates for processing requests
- Serve processed images and result files
- Handle webhook registrations

### 3.2 Asynchronous Worker (Celery)

The Celery worker processes image tasks asynchronously, allowing the API to respond quickly to client requests while heavy processing occurs in the background.

#### Key Responsibilities:
- Fetch and process CSV data
- Download original images
- Compress images to 50% quality
- Store processed images
- Update processing status in the database
- Trigger webhooks upon completion

### 3.3 Database (SQLite)

The SQLite database stores all request and product information, including processing status and image URLs.

#### Key Responsibilities:
- Store request metadata and status
- Track product information
- Maintain relationships between requests and products
- Store image URLs (both input and output)
- Track processing progress

### 3.4 File System Storage

The file system is used to store both uploaded CSV files and processed images.

#### Key Responsibilities:
- Store uploaded CSV files in a structured format
- Organize processed images in an accessible manner
- Provide efficient retrieval of images and files

## 4. Database Schema

The database design consists of two primary tables with a one-to-many relationship:

### 4.1 Requests Table

```sql
CREATE TABLE requests (
    id VARCHAR NOT NULL, 
    status VARCHAR, 
    created_at DATETIME, 
    updated_at DATETIME, 
    csv_filename VARCHAR, 
    total_products INTEGER, 
    processed_products INTEGER, 
    webhook_triggered INTEGER, 
    webhook_url VARCHAR, 
    PRIMARY KEY (id)
);
CREATE INDEX ix_requests_id ON requests (id);
```

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Primary key, unique request identifier |
| status | VARCHAR | Current status of the processing request (PENDING, PROCESSING, COMPLETED, FAILED) |
| created_at | DATETIME | Timestamp when the request was created |
| updated_at | DATETIME | Timestamp when the request was last updated |
| csv_filename | VARCHAR | Name of the uploaded CSV file |
| total_products | INTEGER | Total number of products to process |
| processed_products | INTEGER | Number of products successfully processed |
| webhook_triggered | INTEGER | Boolean flag indicating if webhook has been triggered |
| webhook_url | VARCHAR | Optional URL for webhook notifications |

### 4.2 Products Table

```sql
CREATE TABLE products (
    id INTEGER NOT NULL, 
    request_id VARCHAR, 
    serial_number INTEGER, 
    product_name VARCHAR, 
    input_image_urls TEXT, 
    output_image_urls TEXT, 
    status VARCHAR, 
    created_at DATETIME, 
    updated_at DATETIME, 
    PRIMARY KEY (id), 
    FOREIGN KEY(request_id) REFERENCES requests (id)
);
CREATE INDEX ix_products_id ON products (id);
CREATE INDEX ix_products_product_name ON products (product_name);
```

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-incrementing |
| request_id | VARCHAR | Foreign key to requests table |
| serial_number | INTEGER | Serial number from the CSV |
| product_name | VARCHAR | Name of the product |
| input_image_urls | TEXT | JSON string containing original image URLs |
| output_image_urls | TEXT | JSON string containing processed image URLs |
| status | VARCHAR | Processing status for this specific product |
| created_at | DATETIME | Timestamp when the product record was created |
| updated_at | DATETIME | Timestamp when the product record was last updated |

## 5. API Endpoints

### 5.1 Root Endpoint
- **GET /**
  - Returns basic API information and available endpoints
  - Status codes: 200 OK

### 5.2 CSV Upload and Processing
- **POST /api/upload**
  - Accepts a CSV file with image URLs for processing
  - Parameters:
    - `file` (multipart/form-data): CSV file
    - `webhook_url` (optional): URL for completion notifications
  - Returns a request ID for tracking
  - Status codes: 202 Accepted, 400 Bad Request, 422 Unprocessable Entity

### 5.3 Status and Progress Tracking
- **GET /api/status/{request_id}**
  - Check processing status of a specific request
  - Parameters:
    - `request_id` (path): Unique request identifier
  - Returns status and progress information
  - Status codes: 200 OK, 404 Not Found

### 5.4 Detailed Information
- **GET /api/details/{request_id}**
  - Get comprehensive information about a processing request
  - Parameters:
    - `request_id` (path): Unique request identifier
  - Returns detailed information including all products
  - Status codes: 200 OK, 404 Not Found

### 5.5 Download Results
- **GET /api/download/{request_id}**
  - Download the processed CSV file with output image URLs
  - Parameters:
    - `request_id` (path): Unique request identifier
  - Returns a CSV file with original data plus processed image URLs
  - Status codes: 200 OK, 404 Not Found, 409 Conflict (if processing not complete)

### 5.6 Image Access
- **GET /api/image/{filename}**
  - Serve processed image files
  - Parameters:
    - `filename` (path): Name of the image file
  - Returns the image file with appropriate content type
  - Status codes: 200 OK, 404 Not Found

## 6. Asynchronous Processing Flow

### 6.1 Task Queue Implementation

The system uses Celery as the distributed task queue with Redis serving as both the message broker and result backend. This allows for reliable task distribution and execution across multiple workers.

### 6.2 Processing Sequence

1. User uploads CSV file through the API
2. API validates CSV format and content
3. API creates a request record in the database
4. API queues an asynchronous task for processing
5. API returns request ID to the user immediately
6. Celery worker picks up the task and begins processing:
   - Parses CSV data
   - Creates product records in the database
   - For each product:
     - Downloads original images
     - Compresses images to 50% quality
     - Saves processed images
     - Updates database with output URLs
   - Updates request status upon completion
   - Triggers webhook if provided

### 6.3 Webhook Notification Flow

When image processing is complete, the system can notify an external service through a webhook:

1. User provides webhook URL during upload
2. URL is stored with the request
3. Upon completion of all processing:
   - System sends POST request to webhook URL
   - Request includes request ID, status, and completion information
   - Webhook delivery status is recorded

## 7. CSV Validation Process

The system implements a thorough validation process for uploaded CSV files:

### 7.1 Validation Steps
1. **Initial File Validation**
   - Checks file extension (.csv)
   - Validates file can be opened and read
   - Ensures file is not empty

2. **Structure Validation**
   - Verifies required columns are present
   - Checks column names for exact matches
   - Ensures no required columns are missing

3. **Data Content Validation**
   - Serial Numbers: Must be numeric and unique
   - Product Names: Cannot be empty
   - Image URLs: Must contain at least one valid URL

4. **Error Handling**
   - Provides specific error messages
   - Includes row numbers in error messages
   - Cleans up temporary files on validation failure

## 8. Image Processing Workflow

### 8.1 Image Handling Process
1. **Image Download**
   - System downloads original images from provided URLs
   - Validates image file format and content
   - Handles connection errors and timeouts

2. **Image Compression**
   - Reduces image quality to 50% of original
   - Maintains original dimensions and format
   - Optimizes file size while preserving visual quality

3. **Image Storage**
   - Processed images stored in structured directory
   - File naming convention ensures uniqueness
   - Directory structure allows for efficient retrieval

## 9. Project Structure

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

## 10. Error Handling and Security Considerations

### 10.1 Error Handling Strategy
- Comprehensive error handling for all API endpoints
- Specific error messages for different failure scenarios
- Appropriate HTTP status codes for different error types
- Graceful failure handling in asynchronous tasks

### 10.2 Security Measures
- Input validation for all API parameters
- Sanitization of file names and paths
- Protection against directory traversal attacks
- Validation of webhook URLs
- Rate limiting on API endpoints

## 11. Sequence Diagrams

### 11.1 CSV Upload Flow

```
┌──────┐      ┌────────┐      ┌──────────┐      ┌────────┐      ┌──────────┐
│Client│      │FastAPI │      │Database  │      │Celery  │      │File      │
│      │      │Server  │      │          │      │Worker  │      │System    │
└──┬───┘      └───┬────┘      └────┬─────┘      └───┬────┘      └────┬─────┘
   │              │                │                │                │
   │  Upload CSV  │                │                │                │
   │─────────────>│                │                │                │
   │              │                │                │                │
   │              │ Validate CSV   │                │                │
   │              │─────────────────                │                │
   │              │                │                │                │
   │              │ Create Request │                │                │
   │              │───────────────>│                │                │
   │              │                │                │                │
   │              │                │                │                │
   │              │ Queue Task     │                │                │
   │              │─────────────────────────────────>                │
   │              │                │                │                │
   │ Return ID    │                │                │                │
   │<─────────────│                │                │                │
   │              │                │                │                │
   │              │                │  Process Task  │                │
   │              │                │<───────────────│                │
   │              │                │                │                │
   │              │                │  Update Status │                │
   │              │                │<───────────────│                │
   │              │                │                │ Store Images   │
   │              │                │                │───────────────>│
   │              │                │                │                │
   │              │                │  Final Update  │                │
   │              │                │<───────────────│                │
   │              │                │                │                │
┌──┴───┐      ┌───┴────┐      ┌────┴─────┐      ┌───┴────┐      ┌────┴─────┐
│Client│      │FastAPI │      │Database  │      │Celery  │      │File      │
│      │      │Server  │      │          │      │Worker  │      │System    │
└──────┘      └────────┘      └──────────┘      └────────┘      └──────────┘
```

### 11.2 Status Check Flow

```
┌──────┐      ┌────────┐      ┌──────────┐
│Client│      │FastAPI │      │Database  │
│      │      │Server  │      │          │
└──┬───┘      └───┬────┘      └────┬─────┘
   │              │                │
   │  Status Check│                │
   │─────────────>│                │
   │              │ Query Status   │
   │              │───────────────>│
   │              │                │
   │              │ Return Data    │
   │              │<───────────────│
   │              │                │
   │ Status Response               │
   │<─────────────│                │
   │              │                │
┌──┴───┐      ┌───┴────┐      ┌────┴─────┐
│Client│      │FastAPI │      │Database  │
│      │      │Server  │      │          │
└──────┘      └────────┘      └──────────┘
```

### 11.3 Webhook Notification Flow

```
┌───────┐      ┌────────┐      ┌─────────┐      ┌──────────┐
│Celery │      │Database│      │FastAPI  │      │External  │
│Worker │      │        │      │Server   │      │Service   │
└───┬───┘      └───┬────┘      └────┬────┘      └────┬─────┘
    │              │                │                 │
    │ Task Complete│                │                 │
    │              │                │                 │
    │ Update Status│                │                 │
    │──────────────>                │                 │
    │              │                │                 │
    │ Get Webhook  │                │                 │
    │──────────────>                │                 │
    │              │                │                 │
    │ Return URL   │                │                 │
    │<──────────────                │                 │
    │              │                │                 │
    │ Trigger Webhook               │                 │
    │────────────────────────────────────────────────>│
    │              │                │                 │
    │              │                │                 │
    │ Mark Webhook Triggered        │                 │
    │──────────────>                │                 │
    │              │                │                 │
┌───┴───┐      ┌───┴────┐      ┌────┴────┐      ┌────┴─────┐
│Celery │      │Database│      │FastAPI  │      │External  │
│Worker │      │        │      │Server   │      │Service   │
└───────┘      └────────┘      └─────────┘      └──────────┘
```

## 12. Conclusion

This low-level design document provides a comprehensive overview of the image processing system's architecture, components, and workflows. The system implements all required functionality including CSV validation, asynchronous image processing, status tracking, and webhook notifications.
