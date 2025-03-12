import csv
import pandas as pd
import uuid
import os
from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Optional

from app.database.db import Request, Product, ProcessingStatus
from app.config import UPLOAD_DIR

class CSVValidationError(Exception):
    pass

def validate_csv_format(file_path):
    """Validate the CSV file format."""
    try:
        # First read the raw CSV file to properly handle the URLs
        with open(file_path, 'r') as f:
            header = f.readline().strip().split(',')
            if not all(col in header for col in ["S. No.", "Product Name", "Input Image Urls"]):
                raise CSVValidationError("Missing required columns")
            
            if len(header) != 3:  # Ensure we have exactly 3 columns
                raise CSVValidationError("Invalid number of columns")
            
            # Read and validate each line
            data = []
            for idx, line in enumerate(f, 1):
                # Get everything after the first two commas as the URL string
                parts = line.strip().split(',', 2)
                if len(parts) != 3:
                    raise CSVValidationError(f"Missing data in row {idx}")
                
                serial_no, product_name, urls = parts
                
                if not serial_no or not product_name or not urls:
                    raise CSVValidationError(f"Missing data in row {idx}")
                
                # Validate URLs
                url_list = [url.strip() for url in urls.split(',')]
                if not url_list or any(not url.startswith('http') for url in url_list):
                    raise CSVValidationError(f"Invalid image URL format in row {idx}")
                
                data.append({
                    "S. No.": serial_no,
                    "Product Name": product_name,
                    "Input Image Urls": urls
                })
        
        # Convert to DataFrame after validation
        return pd.DataFrame(data)
    
    except Exception as e:
        if isinstance(e, CSVValidationError):
            raise
        raise CSVValidationError(f"Error validating CSV: {str(e)}")

def process_csv_file(file_path, db: Session, webhook_url: Optional[str] = None):
    """Process the CSV file and store data in the database."""
    # Validate CSV format
    df = validate_csv_format(file_path)
    
    # Create a new request
    request_id = str(uuid.uuid4())
    filename = os.path.basename(file_path)
    
    new_request = Request(
        id=request_id,
        status=ProcessingStatus.PENDING,
        csv_filename=filename,
        total_products=len(df),
        processed_products=0,
        webhook_url=webhook_url
    )
    db.add(new_request)
    
    # Add products to the database
    for idx, row in df.iterrows():
        serial_number = row["S. No."]
        product_name = row["Product Name"]
        input_urls = [url.strip() for url in row["Input Image Urls"].split(",")]
        
        new_product = Product(
            request_id=request_id,
            serial_number=serial_number,
            product_name=product_name,
            input_image_urls=json.dumps(input_urls),
            status=ProcessingStatus.PENDING
        )
        db.add(new_product)
    
    db.commit()
    return request_id

def generate_output_csv(request_id, db: Session):
    """Generate output CSV data for a completed request."""
    # Get request and products
    request = db.query(Request).filter(Request.id == request_id).first()
    if not request or request.status != ProcessingStatus.COMPLETED:
        return None
    
    products = db.query(Product).filter(Product.request_id == request_id).all()
    
    # Prepare data for the CSV
    data = []
    for product in products:
        input_urls = product.get_input_urls()
        output_urls = product.get_output_urls()
        
        data.append({
            "S. No.": product.serial_number,
            "Product Name": product.product_name,
            "Input Image Urls": ','.join(input_urls),
            "Output Image Urls": ','.join(output_urls)
        })
    
    # Create DataFrame and save to CSV
    # df = pd.DataFrame(data)
    output_path = os.path.join(UPLOAD_DIR, f"output_{request_id}.csv")
    # df.to_csv(output_path, 
    #           index=False, 
    #           quoting=csv.QUOTE_MINIMAL,  # This prevents automatic quoting
    #           escapechar='\\',  # Use backslash to escape any special characters
    #           sep=',')
    with open(output_path, 'w') as f:
        f.write("S. No.,Product Name,Input Image Urls,Output Image Urls\n")
        
        # Write each row manually
        for product in products:
            input_urls = product.get_input_urls()
            output_urls = product.get_output_urls()
            
            row = f"{product.serial_number},{product.product_name},{','.join(input_urls)},{','.join(output_urls)}\n"
            f.write(row)
    
    return output_path