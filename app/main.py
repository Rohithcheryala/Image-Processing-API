from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from app.api.endpoints import router
from app.database.db import create_tables

app = FastAPI(
    title="Image Processing API",
    description="API for processing images from CSV data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Error handling
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Create database tables
@app.on_event("startup")
def startup_event():
    create_tables()

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Image Processing API",
        "docs": "/docs",
        "endpoints": [
            "/api/upload - Upload CSV file",
            "/api/status/{request_id} - Check processing status",
            "/api/details/{request_id} - Get detailed request information",
            "/api/download/{request_id} - Download processed CSV"
            "/api/image/{filename} - Download processed image"
        ]
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)