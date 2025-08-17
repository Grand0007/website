from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
from typing import Optional, List
import logging

from routers import auth, resume, ai_engine, user
from database import database
from services.azure_service import AzureService
from services.auth_service import AuthService
from models.schemas import UserCreate, ResumeUpdate, JobDescription

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Resume Updater",
    description="AI-powered resume customization platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.azurewebsites.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
azure_service = AzureService()
auth_service = AuthService()

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    try:
        await database.connect()
        logger.info("Database connected successfully")
        
        # Initialize Azure services
        await azure_service.initialize()
        logger.info("Azure services initialized")
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await database.disconnect()
    logger.info("Database disconnected")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "AI Resume Updater",
        "version": "1.0.0"
    }

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(ai_engine.router, prefix="/api/ai", tags=["ai-engine"])
app.include_router(user.router, prefix="/api/user", tags=["user"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to AI Resume Updater API",
        "docs": "/api/docs",
        "health": "/api/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )