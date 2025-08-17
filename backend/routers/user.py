from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from models.schemas import User, UserUpdate, SuccessResponse
from routers.auth import get_current_active_user
from database import db_manager, users_table
from services.azure_service import azure_service
import logging
from datetime import datetime
from sqlalchemy import update

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/profile", response_model=User)
async def get_user_profile(current_user: dict = Depends(get_current_active_user)):
    """Get current user profile"""
    try:
        return User(**current_user)
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.put("/profile", response_model=User)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update user profile"""
    try:
        update_data = {}
        
        if user_update.first_name is not None:
            update_data["first_name"] = user_update.first_name
        if user_update.last_name is not None:
            update_data["last_name"] = user_update.last_name
        if user_update.is_active is not None:
            update_data["is_active"] = user_update.is_active
        
        if not update_data:
            # No updates provided, return current user
            return User(**current_user)
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update user in database
        query = (
            update(users_table)
            .where(users_table.c.id == current_user["id"])
            .values(**update_data)
        )
        
        await db_manager.execute_query(query)
        
        # Get updated user
        updated_user_query = "SELECT * FROM users WHERE id = :user_id"
        updated_user = await db_manager.fetch_one(
            updated_user_query, 
            {"user_id": current_user["id"]}
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found after update"
            )
        
        return User(**dict(updated_user))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

@router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_active_user)):
    """Get user statistics and activity summary"""
    try:
        # Get resume count
        resume_count_query = "SELECT COUNT(*) as count FROM resumes WHERE user_id = :user_id"
        resume_count_result = await db_manager.fetch_one(
            resume_count_query, 
            {"user_id": current_user["id"]}
        )
        resume_count = resume_count_result["count"] if resume_count_result else 0
        
        # Get AI processing count
        ai_processing_query = "SELECT COUNT(*) as count FROM ai_processing_logs WHERE resume_id IN (SELECT id FROM resumes WHERE user_id = :user_id)"
        ai_processing_result = await db_manager.fetch_one(
            ai_processing_query, 
            {"user_id": current_user["id"]}
        )
        ai_processing_count = ai_processing_result["count"] if ai_processing_result else 0
        
        # Get recent activity
        recent_activity_query = """
            SELECT 
                r.title as resume_title,
                r.created_at,
                r.status,
                'resume_upload' as activity_type
            FROM resumes r 
            WHERE r.user_id = :user_id
            
            UNION ALL
            
            SELECT 
                r.title as resume_title,
                apl.created_at,
                apl.status,
                'ai_processing' as activity_type
            FROM ai_processing_logs apl
            JOIN resumes r ON apl.resume_id = r.id
            WHERE r.user_id = :user_id
            
            ORDER BY created_at DESC
            LIMIT 10
        """
        
        recent_activity = await db_manager.fetch_all(
            recent_activity_query,
            {"user_id": current_user["id"]}
        )
        
        # Get storage usage (approximate)
        storage_query = "SELECT SUM(file_size) as total_size FROM resumes WHERE user_id = :user_id"
        storage_result = await db_manager.fetch_one(
            storage_query,
            {"user_id": current_user["id"]}
        )
        total_storage = storage_result["total_size"] if storage_result and storage_result["total_size"] else 0
        
        return {
            "user_id": current_user["id"],
            "member_since": current_user["created_at"],
            "stats": {
                "total_resumes": resume_count,
                "ai_processing_count": ai_processing_count,
                "storage_used_bytes": total_storage,
                "storage_used_mb": round(total_storage / (1024 * 1024), 2) if total_storage else 0
            },
            "recent_activity": [dict(activity) for activity in recent_activity],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )

@router.get("/resumes/summary")
async def get_user_resumes_summary(current_user: dict = Depends(get_current_active_user)):
    """Get summary of all user resumes"""
    try:
        query = """
            SELECT 
                id,
                title,
                file_name,
                file_size,
                status,
                created_at,
                updated_at,
                JSON_LENGTH(skills) as skills_count,
                JSON_LENGTH(experience) as experience_count,
                JSON_LENGTH(education) as education_count
            FROM resumes 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC
        """
        
        resumes = await db_manager.fetch_all(query, {"user_id": current_user["id"]})
        
        # Calculate summary statistics
        total_resumes = len(resumes)
        total_size = sum(resume["file_size"] for resume in resumes)
        status_counts = {}
        
        for resume in resumes:
            status = resume["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "user_id": current_user["id"],
            "summary": {
                "total_resumes": total_resumes,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
                "status_breakdown": status_counts
            },
            "resumes": [
                {
                    "id": resume["id"],
                    "title": resume["title"],
                    "file_name": resume["file_name"],
                    "file_size_mb": round(resume["file_size"] / (1024 * 1024), 2),
                    "status": resume["status"],
                    "created_at": resume["created_at"],
                    "updated_at": resume["updated_at"],
                    "sections": {
                        "skills_count": resume["skills_count"] or 0,
                        "experience_count": resume["experience_count"] or 0,
                        "education_count": resume["education_count"] or 0
                    }
                }
                for resume in resumes
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting resumes summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resumes summary"
        )

@router.delete("/account", response_model=SuccessResponse)
async def delete_user_account(current_user: dict = Depends(get_current_active_user)):
    """Delete user account and all associated data"""
    try:
        user_id = current_user["id"]
        
        # Get all user's resumes to delete files from Azure
        resumes_query = "SELECT file_path FROM resumes WHERE user_id = :user_id"
        user_resumes = await db_manager.fetch_all(resumes_query, {"user_id": user_id})
        
        # Delete files from Azure Storage
        if azure_service.is_available():
            for resume in user_resumes:
                try:
                    await azure_service.delete_file(resume["file_path"])
                except Exception as e:
                    logger.warning(f"Failed to delete file {resume['file_path']}: {str(e)}")
        
        # Delete user data from database (in order due to foreign keys)
        # Delete AI processing logs first
        await db_manager.execute_query(
            "DELETE FROM ai_processing_logs WHERE resume_id IN (SELECT id FROM resumes WHERE user_id = :user_id)",
            {"user_id": user_id}
        )
        
        # Delete resumes
        await db_manager.execute_query(
            "DELETE FROM resumes WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        
        # Delete OTP codes
        await db_manager.execute_query(
            "DELETE FROM otp_codes WHERE email = :email",
            {"email": current_user["email"]}
        )
        
        # Finally delete user
        await db_manager.execute_query(
            "DELETE FROM users WHERE id = :user_id",
            {"user_id": user_id}
        )
        
        logger.info(f"User account deleted: {current_user['email']}")
        
        return SuccessResponse(
            success=True,
            message="Account deleted successfully",
            data={"deleted_user_id": user_id}
        )
        
    except Exception as e:
        logger.error(f"Error deleting user account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )

@router.get("/export-data")
async def export_user_data(current_user: dict = Depends(get_current_active_user)):
    """Export all user data (GDPR compliance)"""
    try:
        user_id = current_user["id"]
        
        # Get user profile
        user_data = dict(current_user)
        
        # Get all resumes
        resumes_query = "SELECT * FROM resumes WHERE user_id = :user_id"
        resumes = await db_manager.fetch_all(resumes_query, {"user_id": user_id})
        
        # Get AI processing logs
        ai_logs_query = """
            SELECT apl.* FROM ai_processing_logs apl
            JOIN resumes r ON apl.resume_id = r.id
            WHERE r.user_id = :user_id
        """
        ai_logs = await db_manager.fetch_all(ai_logs_query, {"user_id": user_id})
        
        # Get OTP codes history (without actual codes for security)
        otp_query = "SELECT email, created_at, is_used FROM otp_codes WHERE email = :email"
        otp_history = await db_manager.fetch_all(otp_query, {"email": current_user["email"]})
        
        export_data = {
            "export_generated_at": datetime.utcnow().isoformat(),
            "user_profile": user_data,
            "resumes": [dict(resume) for resume in resumes],
            "ai_processing_logs": [dict(log) for log in ai_logs],
            "otp_history": [dict(otp) for otp in otp_history],
            "summary": {
                "total_resumes": len(resumes),
                "total_ai_processing": len(ai_logs),
                "total_otp_requests": len(otp_history)
            }
        }
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting user data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )

@router.get("/preferences")
async def get_user_preferences(current_user: dict = Depends(get_current_active_user)):
    """Get user preferences and settings"""
    try:
        # For now, return default preferences
        # In a real implementation, you'd store these in the database
        preferences = {
            "user_id": current_user["id"],
            "email_notifications": True,
            "ai_customization_level": "moderate",
            "auto_save_customizations": True,
            "theme": "light",
            "language": "en",
            "timezone": "UTC"
        }
        
        return preferences
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences"
        )

@router.put("/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Update user preferences and settings"""
    try:
        # For now, just return the preferences as if they were saved
        # In a real implementation, you'd validate and store these in the database
        
        allowed_preferences = [
            "email_notifications",
            "ai_customization_level", 
            "auto_save_customizations",
            "theme",
            "language",
            "timezone"
        ]
        
        # Filter to only allowed preferences
        filtered_preferences = {
            key: value for key, value in preferences.items() 
            if key in allowed_preferences
        }
        
        # Add user ID and timestamp
        filtered_preferences["user_id"] = current_user["id"]
        filtered_preferences["updated_at"] = datetime.utcnow().isoformat()
        
        return SuccessResponse(
            success=True,
            message="Preferences updated successfully",
            data=filtered_preferences
        )
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )