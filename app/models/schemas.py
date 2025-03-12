from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadRequest(BaseModel):
    webhook_url: Optional[str] = None  # Optional webhook URL

class UploadResponse(BaseModel):
    request_id: str
    message: str
    status: ProcessingStatus
    webhook_url: Optional[str] = None  # Add this to show configured webhook URL

class StatusResponse(BaseModel):
    request_id: str
    status: ProcessingStatus
    progress: dict = Field(default_factory=dict)
    message: str
    created_at: datetime
    updated_at: datetime

class ProductResponse(BaseModel):
    serial_number: int
    product_name: str
    input_image_urls: List[str]
    output_image_urls: Optional[List[str]] = None
    status: ProcessingStatus

class RequestDetailsResponse(StatusResponse):
    products: List[ProductResponse] = []
    csv_filename: str
    total_products: int
    processed_products: int
    completion_percentage: float = 0.0

class WebhookPayload(BaseModel):
    request_id: str
    status: ProcessingStatus
    total_products: int
    processed_products: int
    completion_percentage: float
    timestamp: datetime