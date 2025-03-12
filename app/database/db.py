from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from enum import Enum
import json

from app.config import DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, default=ProcessingStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    csv_filename = Column(String)
    total_products = Column(Integer, default=0)
    processed_products = Column(Integer, default=0)
    webhook_triggered = Column(Integer, default=0)  # 0=not triggered, 1=triggered
    webhook_url = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="request")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("requests.id"))
    serial_number = Column(Integer)
    product_name = Column(String, index=True)
    input_image_urls = Column(Text)  # Stored as JSON string
    output_image_urls = Column(Text, nullable=True)  # Stored as JSON string
    status = Column(String, default=ProcessingStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    request = relationship("Request", back_populates="products")
    
    def get_input_urls(self):
        return json.loads(self.input_image_urls)
    
    def set_input_urls(self, urls):
        self.input_image_urls = json.dumps(urls)
    
    def get_output_urls(self):
        if not self.output_image_urls:
            return []
        return json.loads(self.output_image_urls)
    
    def set_output_urls(self, urls):
        self.output_image_urls = json.dumps(urls)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()