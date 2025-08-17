from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional
from models.schemas import (
    AIResumeRequest, AIResumeResponse, JobDescription, 
    ResumeAnalysis, SuccessResponse
)
from services.ai_service import ai_service
from services.file_service import file_service
from services.azure_service import azure_service
from routers.auth import get_current_active_user
from database import db_manager, ai_processing_logs_table
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze-match", response_model=ResumeAnalysis)
async def analyze_resume_job_match(
    resume_id: str,
    job_description: JobDescription,
    current_user: dict = Depends(get_current_active_user)
):
    """Analyze how well a resume matches a job description"""
    try:
        # Get resume
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Perform analysis
        analysis = await ai_service.analyze_resume_job_match(
            resume["content"], 
            job_description
        )
        
        # Log the analysis
        await _log_ai_activity(
            resume_id, 
            "job_match_analysis",
            {
                "job_title": job_description.title,
                "company": job_description.company,
                "match_score": analysis.job_match_score,
                "missing_skills_count": len(analysis.missing_skills)
            }
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing resume-job match: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze resume-job match"
        )

@router.post("/customize-resume", response_model=AIResumeResponse)
async def customize_resume(
    request: AIResumeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """Customize resume based on job description using AI"""
    try:
        # Get resume
        resume = await file_service.get_resume_by_id(request.resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Start processing log
        processing_start = time.time()
        
        # Update resume status to processing
        from sqlalchemy import update
        query = (
            update(file_service.resumes_table)
            .where(file_service.resumes_table.c.id == request.resume_id)
            .values(status="processing")
        )
        await db_manager.execute_query(query)
        
        try:
            # Perform AI customization
            result = await ai_service.customize_resume(request, resume["content"])
            
            # Save customized resume as a new version or update existing
            customized_resume_id = await _save_customized_resume(
                resume, 
                result.customized_resume, 
                request.job_description,
                current_user["id"]
            )
            
            # Update resume status to completed
            query = (
                update(file_service.resumes_table)
                .where(file_service.resumes_table.c.id == request.resume_id)
                .values(status="completed")
            )
            await db_manager.execute_query(query)
            
            # Log the processing
            processing_time = time.time() - processing_start
            background_tasks.add_task(
                _log_ai_activity,
                request.resume_id,
                "resume_customization",
                {
                    "job_title": request.job_description.title,
                    "company": request.job_description.company,
                    "customization_level": request.customization_level,
                    "match_score": result.match_score,
                    "processing_time": processing_time,
                    "changes_count": len(result.changes_made),
                    "customized_resume_id": customized_resume_id
                }
            )
            
            # Add customized resume ID to response
            result.resume_id = customized_resume_id
            
            return result
            
        except Exception as e:
            # Update resume status to failed
            query = (
                update(file_service.resumes_table)
                .where(file_service.resumes_table.c.id == request.resume_id)
                .values(status="failed")
            )
            await db_manager.execute_query(query)
            
            # Log the error
            background_tasks.add_task(
                _log_ai_activity,
                request.resume_id,
                "resume_customization_failed",
                {
                    "error": str(e),
                    "job_title": request.job_description.title,
                    "customization_level": request.customization_level
                }
            )
            
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error customizing resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to customize resume"
        )

@router.get("/processing-logs/{resume_id}")
async def get_processing_logs(
    resume_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get AI processing logs for a resume"""
    try:
        # Verify resume belongs to user
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        # Get logs from database
        query = """
            SELECT * FROM ai_processing_logs 
            WHERE resume_id = :resume_id 
            ORDER BY created_at DESC 
            LIMIT 50
        """
        
        logs = await db_manager.fetch_all(query, {"resume_id": resume_id})
        
        # Also try to get logs from Azure if available
        azure_logs = []
        if azure_service.is_available():
            try:
                azure_logs = await azure_service.get_processing_logs(resume_id)
            except Exception as e:
                logger.warning(f"Failed to get Azure logs: {str(e)}")
        
        return {
            "resume_id": resume_id,
            "database_logs": [dict(log) for log in logs],
            "azure_logs": azure_logs,
            "total_logs": len(logs) + len(azure_logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processing logs"
        )

@router.post("/batch-analyze")
async def batch_analyze_resumes(
    job_description: JobDescription,
    resume_ids: List[str],
    current_user: dict = Depends(get_current_active_user)
):
    """Analyze multiple resumes against a job description"""
    try:
        if len(resume_ids) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 resumes allowed per batch"
            )
        
        results = []
        
        for resume_id in resume_ids:
            try:
                # Get resume
                resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
                
                if not resume:
                    results.append({
                        "resume_id": resume_id,
                        "error": "Resume not found",
                        "analysis": None
                    })
                    continue
                
                # Perform analysis
                analysis = await ai_service.analyze_resume_job_match(
                    resume["content"], 
                    job_description
                )
                
                results.append({
                    "resume_id": resume_id,
                    "resume_title": resume["title"],
                    "analysis": analysis,
                    "error": None
                })
                
                # Log the analysis
                await _log_ai_activity(
                    resume_id, 
                    "batch_job_match_analysis",
                    {
                        "job_title": job_description.title,
                        "company": job_description.company,
                        "match_score": analysis.job_match_score,
                        "batch_size": len(resume_ids)
                    }
                )
                
            except Exception as e:
                logger.error(f"Error analyzing resume {resume_id}: {str(e)}")
                results.append({
                    "resume_id": resume_id,
                    "error": str(e),
                    "analysis": None
                })
        
        # Sort by match score (highest first)
        successful_results = [r for r in results if r["analysis"] is not None]
        successful_results.sort(
            key=lambda x: x["analysis"].job_match_score, 
            reverse=True
        )
        
        # Combine with failed results
        failed_results = [r for r in results if r["analysis"] is None]
        all_results = successful_results + failed_results
        
        return {
            "job_description": {
                "title": job_description.title,
                "company": job_description.company
            },
            "total_resumes": len(resume_ids),
            "successful_analyses": len(successful_results),
            "failed_analyses": len(failed_results),
            "results": all_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform batch analysis"
        )

@router.get("/suggestions/{resume_id}")
async def get_improvement_suggestions(
    resume_id: str,
    job_description: Optional[JobDescription] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get AI-powered improvement suggestions for a resume"""
    try:
        # Get resume
        resume = await file_service.get_resume_by_id(resume_id, current_user["id"])
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        
        if job_description:
            # Get targeted suggestions for specific job
            analysis = await ai_service.analyze_resume_job_match(
                resume["content"], 
                job_description
            )
            
            suggestions = analysis.suggested_improvements
            context = {
                "type": "job_specific",
                "job_title": job_description.title,
                "company": job_description.company,
                "match_score": analysis.job_match_score,
                "missing_skills": analysis.missing_skills
            }
            
        else:
            # Get general improvement suggestions
            from models.schemas import JobDescription as JD
            
            # Create a generic job description for general analysis
            generic_job = JD(
                title="General Position",
                company="Various Companies",
                description="General professional position requiring relevant skills and experience",
                requirements=["Relevant experience", "Strong communication skills", "Problem-solving abilities"],
                skills_required=["Communication", "Leadership", "Problem Solving", "Teamwork"]
            )
            
            analysis = await ai_service.analyze_resume_job_match(
                resume["content"], 
                generic_job
            )
            
            suggestions = analysis.suggested_improvements
            context = {
                "type": "general",
                "match_score": analysis.job_match_score
            }
        
        return {
            "resume_id": resume_id,
            "suggestions": suggestions,
            "context": context,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate suggestions"
        )

async def _save_customized_resume(
    original_resume: dict, 
    customized_content: dict, 
    job_description: JobDescription,
    user_id: str
) -> str:
    """Save customized resume as a new entry"""
    try:
        import uuid
        from database import resumes_table
        
        customized_id = str(uuid.uuid4())
        
        # Create new resume entry for customized version
        customized_resume_data = {
            "id": customized_id,
            "user_id": user_id,
            "title": f"{original_resume['title']} - Customized for {job_description.title}",
            "file_name": f"customized_{original_resume['file_name']}",
            "file_path": original_resume["file_path"],  # Same file path as original
            "file_size": original_resume["file_size"],
            "content": customized_content,
            "skills": customized_content.get("skills", []),
            "experience": customized_content.get("experience", []),
            "education": customized_content.get("education", []),
            "status": "completed"
        }
        
        # Insert into database
        query = resumes_table.insert().values(**customized_resume_data)
        await db_manager.execute_query(query)
        
        return customized_id
        
    except Exception as e:
        logger.error(f"Error saving customized resume: {str(e)}")
        raise

async def _log_ai_activity(resume_id: str, activity_type: str, details: dict):
    """Log AI processing activity"""
    try:
        # Log to database
        log_data = {
            "resume_id": resume_id,
            "job_description": details.get("job_description", {}),
            "customization_level": details.get("customization_level", ""),
            "match_score": details.get("match_score"),
            "processing_time": details.get("processing_time"),
            "changes_made": details.get("changes_made", []),
            "suggestions": details.get("suggestions", []),
            "status": "completed" if "error" not in details else "failed",
            "error_message": details.get("error")
        }
        
        query = ai_processing_logs_table.insert().values(**log_data)
        await db_manager.execute_query(query)
        
        # Also log to Azure if available
        if azure_service.is_available():
            try:
                await azure_service.log_processing_activity(
                    resume_id, 
                    activity_type, 
                    details
                )
            except Exception as e:
                logger.warning(f"Failed to log to Azure: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error logging AI activity: {str(e)}")
        # Don't raise exception as this is just logging