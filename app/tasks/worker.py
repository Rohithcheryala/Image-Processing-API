import asyncio
from celery import shared_task
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.db import get_db, Product, Request, ProcessingStatus
from app.services.image_service import process_product_images, update_request_status
from app.config import WEBHOOK_URL
from celery_app import celery_app

@celery_app.task(name='process_images_task')
def process_images_task(request_id: str):
    print("yes process_images_task")
    """Process all images for a request."""
    # Run in a separate thread as Celery can't handle asyncio natively
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_process_images(request_id))

async def _process_images(request_id):
    """Asynchronously process all images for a request."""
    # Get database session
    db = next(get_db())

    try:
        # Get all products for the request
        products = db.query(Product).filter(Product.request_id == request_id).all()
        
        # Update request status to processing
        request = db.query(Request).filter(Request.id == request_id).first()
        if request:
            request.status = ProcessingStatus.PROCESSING
            db.commit()
        
        # Process each product's images
        for product in products:
            await process_product_images(product.id, db)
            # Update request status after each product
            await update_request_status(request_id, db)
        
        # Check if completed and trigger webhook if needed
        await trigger_webhook_if_needed(request_id, db)
        
        return {"status": "success", "request_id": request_id}
    except Exception as e:
        # Update request status to failed
        request = db.query(Request).filter(Request.id == request_id).first()
        if request:
            request.status = ProcessingStatus.FAILED
            db.commit()
        
        return {"status": "error", "request_id": request_id, "error": str(e)}
    finally:
        db.close()

async def trigger_webhook_if_needed(request_id, db: Session):
    """Trigger webhook if request is completed and webhook not yet triggered."""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request or request.webhook_triggered or request.status != ProcessingStatus.COMPLETED:
        return
    
    # Use request-specific webhook URL if available, fall back to global config
    webhook_url = request.webhook_url or WEBHOOK_URL
    if not webhook_url:
        return
    
    # Prepare payload
    completion_percentage = (request.processed_products / request.total_products * 100) if request.total_products > 0 else 0
    
    payload = {
        "request_id": request_id,
        "status": request.status,
        "total_products": request.total_products,
        "processed_products": request.processed_products,
        "completion_percentage": completion_percentage,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send webhook
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            # Update webhook triggered status
            request.webhook_triggered = 1
            db.commit()
            
            return True
    except Exception as e:
        print(f"Error triggering webhook for request {request_id}: {str(e)}")
        return False