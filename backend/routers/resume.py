from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional
from models.schemas import Resume, ResumeUpdate, SuccessResponse, PaginatedResponse
from services.file_service import file_service
from routers.auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload", response_model=SuccessResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Upload and parse resume file"""
    try:
        result = await file_service.upload_resume(file, current_user["id"])
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return SuccessResponse(
            success=True,
            message=result["message"],
            data=result["data"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload resume"
        )

@router.get("/", response_model=List[Resume])
async def get_user_resumes(
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all resumes for the authenticated user"""
    try:
        resumes = await file_service.get_user_resumes(
            current_user["id"], 
            limit=limit, 
            offset=offset
        )
        
        return [Resume(**resume) for resume in resumes]
        
    except Exception as e:
        logger.error(f"Error getting user resumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes"
        )

@router.get("/{resume_id}", response_model=Resume)
async def get_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get specific resume by ID"""
    try:
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        return Resume(**resume)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume"
        )

@router.put("/{resume_id}", response_model=Resume)
async def update_resume(
    resume_id: str,
    resume_update: ResumeUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update resume information"""
    try:
        # First check if resume exists and belongs to user
        existing_resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not existing_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Update resume in database
        from database import db_manager, resumes_table
        
        update_data = {}
        if resume_update.title is not None:
            update_data["title"] = resume_update.title
        if resume_update.content is not None:
            update_data["content"] = resume_update.content
        if resume_update.skills is not None:
            update_data["skills"] = resume_update.skills
        if resume_update.experience is not None:
            update_data["experience"] = resume_update.experience
        if resume_update.education is not None:
            update_data["education"] = resume_update.education
        
        if update_data:
            from sqlalchemy import update
            from datetime import datetime
            
            update_data["updated_at"] = datetime.utcnow()
            
            query = (
                update(resumes_table)
                .where(resumes_table.c.id == resume_id)
                .where(resumes_table.c.user_id == current_user["id"])
                .values(**update_data)
            )
            
            await db_manager.execute_query(query)
        
        # Get updated resume
        updated_resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        return Resume(**updated_resume)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resume"
        )

@router.delete("/{resume_id}", response_model=SuccessResponse)
async def delete_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Delete resume"""
    try:
        success = await file_service.delete_resume(resume_id, current_user["id"])
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        return SuccessResponse(
            success=True,
            message="Resume deleted successfully",
            data={"resume_id": resume_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume"
        )

@router.get("/{resume_id}/download")
async def download_resume(
    resume_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Download original resume file"""
    try:
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Get file from Azure Storage
        from services.azure_service import azure_service
        
        try:
            file_url = await azure_service.get_file_url(
                resume["file_path"], 
                expires_in_hours=1
            )
            
            return {
                "download_url": file_url,
                "filename": resume["file_name"],
                "expires_in": 3600  # 1 hour
            }
            
        except Exception:
            # If Azure is not available, return error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File download service temporarily unavailable"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download resume"
        )

@router.get("/{resume_id}/content")
async def get_resume_content(
    resume_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get parsed resume content"""
    try:
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        return {
            "resume_id": resume["id"],
            "title": resume["title"],
            "content": resume["content"],
            "skills": resume["skills"],
            "experience": resume["experience"],
            "education": resume["education"],
            "parsed_at": resume["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume content {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume content"
        )