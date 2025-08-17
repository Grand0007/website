import os
import io
import json
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import aiofiles
import PyPDF2
from docx import Document
import re
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from services.azure_service import azure_service
from database import db_manager, resumes_table
from models.schemas import FileUploadResponse, ResumeCreate

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 10485760))  # 10MB
        self.allowed_extensions = os.getenv("ALLOWED_FILE_TYPES", "pdf,docx,doc").split(',')
        self.upload_dir = "uploads"
        
        # Ensure upload directory exists
        Path(self.upload_dir).mkdir(exist_ok=True)

    async def upload_resume(self, file, user_id: str) -> Dict[str, Any]:
        """Upload and process resume file"""
        try:
            # Validate file
            validation_result = self._validate_file(file)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": validation_result["message"]
                }
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{file_id}{file_extension}"
            
            # Read file content
            file_content = await file.read()
            
            # Save file locally temporarily
            temp_file_path = Path(self.upload_dir) / unique_filename
            async with aiofiles.open(temp_file_path, 'wb') as f:
                await f.write(file_content)
            
            # Parse resume content
            parsed_content = await self._parse_resume(temp_file_path, file_extension)
            
            # Upload to Azure Storage
            azure_file_path = await azure_service.upload_file(
                file_content, 
                unique_filename,
                container_name="resumes"
            )
            
            # Save resume record to database
            resume_data = {
                "id": file_id,
                "user_id": user_id,
                "title": parsed_content.get("title", file.filename),
                "file_name": file.filename,
                "file_path": azure_file_path,
                "file_size": len(file_content),
                "content": parsed_content,
                "skills": parsed_content.get("skills", []),
                "experience": parsed_content.get("experience", []),
                "education": parsed_content.get("education", []),
                "status": "uploaded"
            }
            
            # Insert into database
            query = resumes_table.insert().values(**resume_data)
            await db_manager.execute_query(query)
            
            # Clean up temporary file
            try:
                temp_file_path.unlink()
            except:
                pass
            
            return {
                "success": True,
                "message": "Resume uploaded and processed successfully",
                "data": {
                    "resume_id": file_id,
                    "file_name": file.filename,
                    "file_size": len(file_content),
                    "parsed_content": parsed_content
                }
            }
            
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            return {
                "success": False,
                "message": "Failed to upload resume",
                "error": str(e)
            }

    def _validate_file(self, file) -> Dict[str, Any]:
        """Validate uploaded file"""
        if not file:
            return {"valid": False, "message": "No file provided"}
        
        if not file.filename:
            return {"valid": False, "message": "Invalid filename"}
        
        # Check file extension
        file_extension = Path(file.filename).suffix.lower().lstrip('.')
        if file_extension not in self.allowed_extensions:
            return {
                "valid": False, 
                "message": f"File type not allowed. Supported types: {', '.join(self.allowed_extensions)}"
            }
        
        # Check file size (this is approximate, actual size checked after reading)
        if hasattr(file, 'size') and file.size > self.max_file_size:
            return {
                "valid": False,
                "message": f"File size exceeds maximum limit of {self.max_file_size / 1024 / 1024:.1f}MB"
            }
        
        return {"valid": True, "message": "File validation passed"}

    async def _parse_resume(self, file_path: Path, file_extension: str) -> Dict[str, Any]:
        """Parse resume content based on file type"""
        try:
            if file_extension == '.pdf':
                return await self._parse_pdf(file_path)
            elif file_extension in ['.docx', '.doc']:
                return await self._parse_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error parsing resume {file_path}: {str(e)}")
            return {
                "title": file_path.stem,
                "raw_text": "",
                "personal_info": {},
                "experience": [],
                "education": [],
                "skills": [],
                "projects": [],
                "parse_error": str(e)
            }

    async def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF resume file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # Process extracted text
            return self._extract_resume_data(text)
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise

    async def _parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """Parse DOCX resume file"""
        try:
            doc = Document(file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            # Process extracted text
            return self._extract_resume_data(text)
            
        except Exception as e:
            logger.error(f"Error parsing DOCX: {str(e)}")
            raise

    def _extract_resume_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from resume text using pattern matching"""
        resume_data = {
            "raw_text": text,
            "personal_info": {},
            "experience": [],
            "education": [],
            "skills": [],
            "projects": [],
            "certifications": []
        }
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract personal information
        resume_data["personal_info"] = self._extract_personal_info(lines)
        
        # Extract sections
        resume_data["experience"] = self._extract_experience(text, lines)
        resume_data["education"] = self._extract_education(text, lines)
        resume_data["skills"] = self._extract_skills(text, lines)
        resume_data["projects"] = self._extract_projects(text, lines)
        resume_data["certifications"] = self._extract_certifications(text, lines)
        
        # Generate title from personal info or filename
        name = resume_data["personal_info"].get("name", "")
        title = resume_data["personal_info"].get("title", "")
        resume_data["title"] = f"{name} - {title}" if name and title else name or "Resume"
        
        return resume_data

    def _extract_personal_info(self, lines: List[str]) -> Dict[str, Any]:
        """Extract personal information from resume"""
        personal_info = {}
        
        # Extract name (usually first non-empty line or largest text)
        if lines:
            personal_info["name"] = lines[0]
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for line in lines[:10]:  # Check first 10 lines
            email_match = re.search(email_pattern, line)
            if email_match:
                personal_info["email"] = email_match.group()
                break
        
        # Extract phone
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        for line in lines[:10]:
            phone_match = re.search(phone_pattern, line)
            if phone_match:
                personal_info["phone"] = phone_match.group()
                break
        
        # Extract LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        for line in lines[:15]:
            linkedin_match = re.search(linkedin_pattern, line.lower())
            if linkedin_match:
                personal_info["linkedin"] = linkedin_match.group()
                break
        
        # Extract location (look for city, state patterns)
        location_pattern = r'\b[A-Za-z\s]+,\s*[A-Z]{2}\b'
        for line in lines[:10]:
            location_match = re.search(location_pattern, line)
            if location_match:
                personal_info["location"] = location_match.group()
                break
        
        return personal_info

    def _extract_experience(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract work experience from resume"""
        experience = []
        
        # Find experience section
        experience_keywords = ['experience', 'work history', 'employment', 'professional experience']
        experience_start = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in experience_keywords):
                experience_start = i
                break
        
        if experience_start == -1:
            return experience
        
        # Extract experience entries
        current_job = {}
        for i in range(experience_start + 1, len(lines)):
            line = lines[i].strip()
            
            # Check if this is a new job (contains company/title patterns)
            if self._is_job_title_line(line):
                if current_job:
                    experience.append(current_job)
                current_job = {"title": line, "description": "", "responsibilities": []}
            
            # Check for date patterns
            elif self._contains_date_range(line):
                if current_job:
                    current_job["duration"] = line
            
            # Add to description
            elif line and current_job:
                if line.startswith('•') or line.startswith('-'):
                    current_job["responsibilities"].append(line.lstrip('•-').strip())
                else:
                    current_job["description"] += " " + line
        
        if current_job:
            experience.append(current_job)
        
        return experience

    def _extract_education(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract education from resume"""
        education = []
        
        education_keywords = ['education', 'academic', 'qualifications']
        education_start = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in education_keywords):
                education_start = i
                break
        
        if education_start == -1:
            return education
        
        # Extract education entries
        degree_patterns = [
            r'\b(bachelor|master|phd|doctorate|associate|diploma|certificate)\b',
            r'\b(b\.?s\.?|m\.?s\.?|m\.?a\.?|ph\.?d\.?|b\.?a\.?)\b'
        ]
        
        current_edu = {}
        for i in range(education_start + 1, min(education_start + 20, len(lines))):
            line = lines[i].strip()
            
            # Check for degree patterns
            for pattern in degree_patterns:
                if re.search(pattern, line.lower()):
                    if current_edu:
                        education.append(current_edu)
                    current_edu = {"degree": line}
                    break
            
            # Check for dates
            if self._contains_date_range(line) and current_edu:
                current_edu["year"] = line
            
            # Check for institution names (usually capitalized)
            elif line and current_edu and "institution" not in current_edu:
                if any(word[0].isupper() for word in line.split()):
                    current_edu["institution"] = line
        
        if current_edu:
            education.append(current_edu)
        
        return education

    def _extract_skills(self, text: str, lines: List[str]) -> List[str]:
        """Extract skills from resume"""
        skills = []
        
        skills_keywords = ['skills', 'technical skills', 'competencies', 'technologies']
        skills_start = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in skills_keywords):
                skills_start = i
                break
        
        if skills_start == -1:
            # Try to extract skills from entire text
            return self._extract_skills_from_text(text)
        
        # Extract skills from skills section
        for i in range(skills_start + 1, min(skills_start + 15, len(lines))):
            line = lines[i].strip()
            
            # Skip section headers
            if any(keyword in line.lower() for keyword in ['experience', 'education', 'projects']):
                break
            
            if line:
                # Split by common delimiters
                skill_parts = re.split(r'[,;•\-\|]', line)
                for skill in skill_parts:
                    skill = skill.strip()
                    if skill and len(skill) > 1:
                        skills.append(skill)
        
        return skills[:20]  # Limit to top 20 skills

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from entire text using common technical keywords"""
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'sql', 'html', 'css',
            'git', 'docker', 'kubernetes', 'aws', 'azure', 'linux', 'windows',
            'machine learning', 'data analysis', 'project management', 'agile',
            'scrum', 'leadership', 'communication', 'problem solving'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return found_skills

    def _extract_projects(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Extract projects from resume"""
        projects = []
        
        project_keywords = ['projects', 'portfolio', 'personal projects']
        project_start = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in project_keywords):
                project_start = i
                break
        
        if project_start == -1:
            return projects
        
        current_project = {}
        for i in range(project_start + 1, min(project_start + 20, len(lines))):
            line = lines[i].strip()
            
            if not line:
                continue
            
            # New project (usually starts with project name)
            if line and not line.startswith('•') and not line.startswith('-'):
                if current_project:
                    projects.append(current_project)
                current_project = {"name": line, "description": ""}
            
            # Project description
            elif current_project:
                current_project["description"] += " " + line.lstrip('•-').strip()
        
        if current_project:
            projects.append(current_project)
        
        return projects

    def _extract_certifications(self, text: str, lines: List[str]) -> List[str]:
        """Extract certifications from resume"""
        certifications = []
        
        cert_keywords = ['certifications', 'certificates', 'licenses']
        cert_start = -1
        
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in cert_keywords):
                cert_start = i
                break
        
        if cert_start == -1:
            return certifications
        
        for i in range(cert_start + 1, min(cert_start + 10, len(lines))):
            line = lines[i].strip()
            if line and not any(keyword in line.lower() for keyword in ['experience', 'education', 'skills']):
                certifications.append(line)
        
        return certifications

    def _is_job_title_line(self, line: str) -> bool:
        """Check if line contains a job title"""
        job_indicators = ['engineer', 'developer', 'manager', 'analyst', 'specialist', 'coordinator', 'director', 'lead']
        return any(indicator in line.lower() for indicator in job_indicators)

    def _contains_date_range(self, line: str) -> bool:
        """Check if line contains a date range"""
        date_patterns = [
            r'\d{4}\s*[-–]\s*\d{4}',
            r'\d{4}\s*[-–]\s*present',
            r'\w+\s+\d{4}\s*[-–]\s*\w+\s+\d{4}',
            r'\w+\s+\d{4}\s*[-–]\s*present'
        ]
        
        return any(re.search(pattern, line.lower()) for pattern in date_patterns)

    async def get_resume_by_id(self, resume_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get resume by ID for the authenticated user"""
        try:
            query = "SELECT * FROM resumes WHERE id = :resume_id AND user_id = :user_id"
            resume = await db_manager.fetch_one(query, {"resume_id": resume_id, "user_id": user_id})
            
            return dict(resume) if resume else None
            
        except Exception as e:
            logger.error(f"Error getting resume {resume_id}: {str(e)}")
            return None

    async def get_user_resumes(self, user_id: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all resumes for a user"""
        try:
            query = """
                SELECT * FROM resumes 
                WHERE user_id = :user_id 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """
            
            resumes = await db_manager.fetch_all(
                query, 
                {"user_id": user_id, "limit": limit, "offset": offset}
            )
            
            return [dict(resume) for resume in resumes]
            
        except Exception as e:
            logger.error(f"Error getting user resumes: {str(e)}")
            return []

    async def delete_resume(self, resume_id: str, user_id: str) -> bool:
        """Delete a resume"""
        try:
            # Get resume info first
            resume = await self.get_resume_by_id(resume_id, user_id)
            if not resume:
                return False
            
            # Delete from Azure Storage
            await azure_service.delete_file(resume["file_path"])
            
            # Delete from database
            query = "DELETE FROM resumes WHERE id = :resume_id AND user_id = :user_id"
            await db_manager.execute_query(query, {"resume_id": resume_id, "user_id": user_id})
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting resume {resume_id}: {str(e)}")
            return False

# Initialize file service
file_service = FileService()