import os
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime
from typing import Optional
import re
from pathlib import Path

from app.database.db import get_db, Request, Product, ProcessingStatus
from app.services.csv_service import validate_csv_format, process_csv_file, CSVValidationError, generate_output_csv
from celery_app import celery_app
from app.models.schemas import UploadResponse, StatusResponse, RequestDetailsResponse, ProductResponse, UploadRequest
from app.config import UPLOAD_DIR, PROCESSED_DIR

router = APIRouter()

@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    background_tasks: BackgroundTasks,
    webhook_url: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file with image URLs for processing.
    Optionally specify a webhook URL for completion notifications.
    
    Returns a unique request ID for tracking the processing status.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    
    if webhook_url and not webhook_url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid webhook URL format")
    
    print(f"webhook_url={webhook_url}")
    # Save the uploaded file
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # Process the CSV file and get request ID
        request_id = process_csv_file(file_path, db, webhook_url)
        
        # Try to start asynchronous processing
        try:
            celery_app.send_task('process_images_task', args=[request_id])
        except Exception as celery_error:
            print(f"Warning: Could not start Celery task: {str(celery_error)}")
            request = db.query(Request).filter(Request.id == request_id).first()
            if request:
                request.status = ProcessingStatus.FAILED
                db.commit()
            raise HTTPException(
                status_code=503, 
                detail="Processing service temporarily unavailable. Please try again later or contact support."
            )
        
        return {
            "request_id": request_id,
            "message": "CSV file uploaded successfully and processing has started",
            "status": ProcessingStatus.PENDING,
            "webhook_url": webhook_url
        }
    except CSVValidationError as e:
        # Clean up file if validation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Clean up file and re-raise HTTP exceptions
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        # Clean up file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@router.get("/status/{request_id}", response_model=StatusResponse)
def check_status(request_id: str, db: Session = Depends(get_db)):
    """
    Check the processing status for a given request ID.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail=f"Request with ID {request_id} not found")
    
    # Calculate progress
    progress = {
        "total_products": request.total_products,
        "processed_products": request.processed_products,
        "percentage": (request.processed_products / request.total_products * 100) if request.total_products > 0 else 0
    }
    
    message = "Processing in progress"
    if request.status == ProcessingStatus.COMPLETED:
        message = "Processing completed successfully"
    elif request.status == ProcessingStatus.FAILED:
        message = "Processing failed"
    elif request.status == ProcessingStatus.PENDING:
        message = "Processing queued, not yet started"
    
    return {
        "request_id": request_id,
        "status": request.status,
        "progress": progress,
        "message": message,
        "created_at": request.created_at,
        "updated_at": request.updated_at
    }

@router.get("/details/{request_id}", response_model=RequestDetailsResponse)
def get_request_details(request_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a processing request, including product details.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail=f"Request with ID {request_id} not found")
    
    # Get all products for this request
    products = db.query(Product).filter(Product.request_id == request_id).all()
    
    # Calculate completion percentage
    completion_percentage = (request.processed_products / request.total_products * 100) if request.total_products > 0 else 0
    
    # Build response
    product_responses = []
    for product in products:
        product_responses.append(ProductResponse(
            serial_number=product.serial_number,
            product_name=product.product_name,
            input_image_urls=product.get_input_urls(),
            output_image_urls=product.get_output_urls() if product.output_image_urls else None,
            status=product.status
        ))
    
    message = "Processing in progress"
    if request.status == ProcessingStatus.COMPLETED:
        message = "Processing completed successfully"
    elif request.status == ProcessingStatus.FAILED:
        message = "Processing failed"
    elif request.status == ProcessingStatus.PENDING:
        message = "Processing queued, not yet started"
    
    progress = {
        "total_products": request.total_products,
        "processed_products": request.processed_products,
        "percentage": completion_percentage
    }
    
    return {
        "request_id": request_id,
        "status": request.status,
        "progress": progress,
        "message": message,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "products": product_responses,
        "csv_filename": request.csv_filename,
        "total_products": request.total_products,
        "processed_products": request.processed_products,
        "completion_percentage": completion_percentage
    }

@router.get("/download/{request_id}")
def download_processed_csv(request_id: str, db: Session = Depends(get_db)):
    """
    Download the processed CSV with output image URLs.
    Only available for completed requests.
    """
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail=f"Request with ID {request_id} not found")
    
    if request.status != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="CSV is only available for completed requests")
    
    # Generate CSV file
    output_path = generate_output_csv(request_id, db)
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Error generating output CSV")
    
    return FileResponse(
        output_path,
        media_type="text/csv",
        filename=f"processed_{request.csv_filename}"
    )

@router.get("/image/{filename}")
async def get_processed_image(filename: str):
    """
    Serve a processed image file by filename.
    """
    # Validate filename format
    if not re.match(r'^[a-zA-Z0-9_-]+\.(jpg|jpeg|png|gif|webp)$', filename.lower()):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename format"
        )
    
    # Ensure no directory traversal is possible
    file_path = Path(PROCESSED_DIR) / filename
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(Path(PROCESSED_DIR).resolve())):
            raise HTTPException(
                status_code=400,
                detail="Invalid file path"
            )
    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Image {filename} not found"
        )
    
    # Map file extensions to content types
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    
    content_type = content_types.get(file_path.suffix.lower(), 'image/jpeg')
    
    return FileResponse(
        str(file_path),
        media_type=content_type,
        filename=filename
    )