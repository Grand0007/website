from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.schemas import OTPRequest, OTPVerify, Token, User, SuccessResponse
from services.auth_service import auth_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.post("/request-otp", response_model=SuccessResponse)
async def request_otp(otp_request: OTPRequest):
    """Request OTP for email authentication"""
    try:
        result = await auth_service.create_otp(otp_request.email)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return SuccessResponse(
            success=True,
            message=result["message"],
            data={"expires_in": result["expires_in"]}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

@router.post("/verify-otp", response_model=Token)
async def verify_otp(otp_verify: OTPVerify):
    """Verify OTP and return access token"""
    try:
        result = await auth_service.verify_otp(otp_verify.email, otp_verify.otp_code)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result["message"]
            )
        
        return Token(
            access_token=result["token"]["access_token"],
            token_type=result["token"]["token_type"],
            expires_in=result["token"]["expires_in"],
            user=User(**result["user"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/me", response_model=User)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return User(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.post("/logout")
async def logout():
    """Logout endpoint (token invalidation handled on client side)"""
    return SuccessResponse(
        success=True,
        message="Logged out successfully",
        data={}
    )

@router.post("/cleanup-expired-otps")
async def cleanup_expired_otps():
    """Admin endpoint to cleanup expired OTP codes"""
    try:
        await auth_service.cleanup_expired_otps()
        return SuccessResponse(
            success=True,
            message="Expired OTP codes cleaned up",
            data={}
        )
    except Exception as e:
        logger.error(f"Error cleaning up OTPs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired OTPs"
        )

# Dependency to get current authenticated user
async def get_current_active_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = await auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user