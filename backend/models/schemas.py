from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool = True

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: str
    role: UserRole
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Authentication Schemas
class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None

# Resume Schemas
class ResumeBase(BaseModel):
    title: str
    content: Dict[str, Any]
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []

class ResumeCreate(ResumeBase):
    pass

class ResumeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None

class Resume(ResumeBase):
    id: str
    user_id: str
    file_path: str
    file_name: str
    file_size: int
    status: ResumeStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Job Description Schema
class JobDescription(BaseModel):
    title: str
    company: str
    description: str
    requirements: List[str] = []
    preferred_qualifications: List[str] = []
    skills_required: List[str] = []
    experience_level: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None

# AI Processing Schemas
class AIResumeRequest(BaseModel):
    resume_id: str
    job_description: JobDescription
    customization_level: str = "moderate"  # light, moderate, heavy
    
    @validator('customization_level')
    def validate_customization_level(cls, v):
        if v not in ['light', 'moderate', 'heavy']:
            raise ValueError('customization_level must be light, moderate, or heavy')
        return v

class AIResumeResponse(BaseModel):
    resume_id: str
    customized_resume: Dict[str, Any]
    changes_made: List[str]
    match_score: float
    suggestions: List[str]
    processing_time: float

class SkillMatch(BaseModel):
    skill: str
    relevance_score: float
    in_resume: bool
    in_job_description: bool

class ResumeAnalysis(BaseModel):
    resume_id: str
    job_match_score: float
    skill_matches: List[SkillMatch]
    missing_skills: List[str]
    suggested_improvements: List[str]
    keyword_density: Dict[str, float]

# File Upload Schemas
class FileUploadResponse(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    file_type: str
    upload_url: Optional[str] = None
    status: str

# Error Schemas
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Success Response Schema
class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Pagination Schema
class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 10
    
    @validator('page')
    def validate_page(cls, v):
        if v < 1:
            raise ValueError('page must be greater than 0')
        return v
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('limit must be between 1 and 100')
        return v

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int