import os
import httpx
import uuid
from PIL import Image
from io import BytesIO
import asyncio
from sqlalchemy.orm import Session

from app.config import PROCESSED_DIR, IMAGE_COMPRESSION_QUALITY, API_BASE_URL
from app.database.db import Product, Request, ProcessingStatus

async def download_image(url):
    """Download an image from a URL."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return BytesIO(response.content)
    except Exception as e:
        print(f"Error downloading image from {url}: {str(e)}")
        return None

def compress_image(image_data, quality=IMAGE_COMPRESSION_QUALITY):
    """Compress an image to reduce its quality by 50%."""
    try:
        img = Image.open(image_data)
        output = BytesIO()
        
        # Save with reduced quality (JPEG format)
        if img.format == 'PNG':
            img = img.convert('RGB')  # Convert PNG to RGB for JPEG saving
        
        img.save(output, format='JPEG', quality=quality)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Error compressing image: {str(e)}")
        return None

async def process_image(url):
    """Download and process a single image."""
    image_data = await download_image(url)
    if not image_data:
        return None
    
    compressed_data = compress_image(image_data)
    if not compressed_data:
        return None
    
    # Generate a unique filename and save the processed image
    filename = f"{uuid.uuid4()}.jpg"
    output_path = os.path.join(PROCESSED_DIR, filename)
    
    # Save the compressed image
    with open(output_path, "wb") as f:
        f.write(compressed_data.getvalue())
    
    print(f"{API_BASE_URL}/api/image/{filename}")
    # Return the proper API endpoint URL for the image
    return f"{API_BASE_URL}/api/image/{filename}"

async def process_product_images(product_id, db: Session):
    """Process all images for a product."""
    # Get the product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return False
    
    # Update product status
    product.status = ProcessingStatus.PROCESSING
    db.commit()
    
    try:
        input_urls = product.get_input_urls()
        output_urls = []
        
        # Process each image
        for url in input_urls:
            print(url)
            processed_url = await process_image(url)
            if processed_url:
                output_urls.append(processed_url)
            else:
                output_urls.append("")  # Placeholder for failed processing
        
        # Update product with processed images
        product.set_output_urls(output_urls)
        product.status = ProcessingStatus.COMPLETED
        db.commit()
        
        return True
    except Exception as e:
        product.status = ProcessingStatus.FAILED
        db.commit()
        print(f"Error processing product {product_id}: {str(e)}")
        return False

async def update_request_status(request_id, db: Session):
    """Update the status of a request based on its products."""
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request:
        return
    
    # Count products by status
    total = db.query(Product).filter(Product.request_id == request_id).count()
    completed = db.query(Product).filter(
        Product.request_id == request_id,
        Product.status == ProcessingStatus.COMPLETED
    ).count()
    failed = db.query(Product).filter(
        Product.request_id == request_id,
        Product.status == ProcessingStatus.FAILED
    ).count()
    
    # Update request stats
    request.processed_products = completed + failed
    
    # Determine overall status
    if completed + failed == total:
        if failed > 0 and completed == 0:
            request.status = ProcessingStatus.FAILED
        else:
            request.status = ProcessingStatus.COMPLETED
    elif completed + failed > 0:
        request.status = ProcessingStatus.PROCESSING
    
    db.commit()