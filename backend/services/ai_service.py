import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
import openai
from openai import OpenAI
import logging
import re
from datetime import datetime
from models.schemas import JobDescription, AIResumeRequest, AIResumeResponse, ResumeAnalysis, SkillMatch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import spacy

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.max_tokens = int(os.getenv("MAX_TOKENS", 2000))
        
        # Initialize NLP components
        self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Initialize NLP libraries and download required data"""
        try:
            # Download NLTK data if not already present
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            
            # Load spaCy model
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
            
            self.stop_words = set(stopwords.words('english'))
            logger.info("NLP components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing NLP components: {str(e)}")

    async def analyze_resume_job_match(self, resume_content: Dict[str, Any], job_description: JobDescription) -> ResumeAnalysis:
        """Analyze how well a resume matches a job description"""
        start_time = time.time()
        
        try:
            # Extract text from resume
            resume_text = self._extract_resume_text(resume_content)
            job_text = self._extract_job_text(job_description)
            
            # Calculate overall match score
            match_score = self._calculate_match_score(resume_text, job_text)
            
            # Analyze skills
            skill_matches = self._analyze_skill_matches(resume_content, job_description)
            
            # Find missing skills
            missing_skills = self._find_missing_skills(resume_content, job_description)
            
            # Generate improvement suggestions
            suggestions = await self._generate_improvement_suggestions(resume_content, job_description, missing_skills)
            
            # Calculate keyword density
            keyword_density = self._calculate_keyword_density(resume_text, job_description)
            
            processing_time = time.time() - start_time
            
            return ResumeAnalysis(
                resume_id=resume_content.get("id", ""),
                job_match_score=match_score,
                skill_matches=skill_matches,
                missing_skills=missing_skills,
                suggested_improvements=suggestions,
                keyword_density=keyword_density
            )
            
        except Exception as e:
            logger.error(f"Error analyzing resume-job match: {str(e)}")
            raise

    async def customize_resume(self, request: AIResumeRequest, resume_content: Dict[str, Any]) -> AIResumeResponse:
        """Customize resume based on job description using AI"""
        start_time = time.time()
        
        try:
            # Analyze current resume-job match
            analysis = await self.analyze_resume_job_match(resume_content, request.job_description)
            
            # Generate customized resume content
            customized_content = await self._generate_customized_resume(
                resume_content, 
                request.job_description, 
                request.customization_level,
                analysis
            )
            
            # Track changes made
            changes_made = self._track_changes(resume_content, customized_content)
            
            # Generate suggestions for further improvement
            suggestions = await self._generate_customization_suggestions(
                customized_content, 
                request.job_description,
                analysis
            )
            
            processing_time = time.time() - start_time
            
            return AIResumeResponse(
                resume_id=request.resume_id,
                customized_resume=customized_content,
                changes_made=changes_made,
                match_score=analysis.job_match_score,
                suggestions=suggestions,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error customizing resume: {str(e)}")
            raise

    def _extract_resume_text(self, resume_content: Dict[str, Any]) -> str:
        """Extract all text from resume content"""
        text_parts = []
        
        # Add basic information
        if 'personal_info' in resume_content:
            personal = resume_content['personal_info']
            text_parts.extend([
                personal.get('name', ''),
                personal.get('title', ''),
                personal.get('summary', ''),
                personal.get('objective', '')
            ])
        
        # Add experience
        if 'experience' in resume_content:
            for exp in resume_content['experience']:
                text_parts.extend([
                    exp.get('title', ''),
                    exp.get('company', ''),
                    exp.get('description', ''),
                    ' '.join(exp.get('responsibilities', []))
                ])
        
        # Add education
        if 'education' in resume_content:
            for edu in resume_content['education']:
                text_parts.extend([
                    edu.get('degree', ''),
                    edu.get('institution', ''),
                    edu.get('field', '')
                ])
        
        # Add skills
        if 'skills' in resume_content:
            text_parts.extend(resume_content['skills'])
        
        # Add projects
        if 'projects' in resume_content:
            for project in resume_content['projects']:
                text_parts.extend([
                    project.get('name', ''),
                    project.get('description', ''),
                    ' '.join(project.get('technologies', []))
                ])
        
        return ' '.join(filter(None, text_parts))

    def _extract_job_text(self, job_description: JobDescription) -> str:
        """Extract all text from job description"""
        text_parts = [
            job_description.title,
            job_description.company,
            job_description.description,
            ' '.join(job_description.requirements),
            ' '.join(job_description.preferred_qualifications),
            ' '.join(job_description.skills_required),
            job_description.experience_level or '',
            job_description.location or ''
        ]
        
        return ' '.join(filter(None, text_parts))

    def _calculate_match_score(self, resume_text: str, job_text: str) -> float:
        """Calculate similarity score between resume and job description"""
        try:
            # Use TF-IDF vectorization
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # Convert to percentage and ensure it's between 0 and 100
            return min(max(similarity * 100, 0), 100)
            
        except Exception as e:
            logger.error(f"Error calculating match score: {str(e)}")
            return 0.0

    def _analyze_skill_matches(self, resume_content: Dict[str, Any], job_description: JobDescription) -> List[SkillMatch]:
        """Analyze skill matches between resume and job description"""
        skill_matches = []
        
        # Extract skills from resume
        resume_skills = set()
        if 'skills' in resume_content:
            resume_skills.update([skill.lower().strip() for skill in resume_content['skills']])
        
        # Extract skills from job description
        job_skills = set()
        job_skills.update([skill.lower().strip() for skill in job_description.skills_required])
        job_skills.update([skill.lower().strip() for skill in job_description.requirements])
        
        # Find all unique skills
        all_skills = resume_skills.union(job_skills)
        
        for skill in all_skills:
            in_resume = skill in resume_skills
            in_job = skill in job_skills
            
            # Calculate relevance score based on presence and context
            relevance_score = 0.5  # Base score
            if in_resume and in_job:
                relevance_score = 1.0
            elif in_resume or in_job:
                relevance_score = 0.7
            
            skill_matches.append(SkillMatch(
                skill=skill.title(),
                relevance_score=relevance_score,
                in_resume=in_resume,
                in_job_description=in_job
            ))
        
        return sorted(skill_matches, key=lambda x: x.relevance_score, reverse=True)

    def _find_missing_skills(self, resume_content: Dict[str, Any], job_description: JobDescription) -> List[str]:
        """Find skills mentioned in job description but missing from resume"""
        resume_skills = set()
        if 'skills' in resume_content:
            resume_skills.update([skill.lower().strip() for skill in resume_content['skills']])
        
        job_skills = set()
        job_skills.update([skill.lower().strip() for skill in job_description.skills_required])
        
        missing_skills = job_skills - resume_skills
        return [skill.title() for skill in missing_skills]

    def _calculate_keyword_density(self, resume_text: str, job_description: JobDescription) -> Dict[str, float]:
        """Calculate keyword density for important job-related terms"""
        job_text = self._extract_job_text(job_description)
        
        # Extract important keywords from job description
        job_words = word_tokenize(job_text.lower())
        job_words = [word for word in job_words if word not in self.stop_words and len(word) > 2]
        
        # Count word frequency in job description
        job_word_freq = {}
        for word in job_words:
            job_word_freq[word] = job_word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_keywords = sorted(job_word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Calculate density in resume
        resume_words = word_tokenize(resume_text.lower())
        resume_word_count = len(resume_words)
        
        keyword_density = {}
        for keyword, _ in top_keywords:
            count = resume_words.count(keyword)
            density = (count / resume_word_count) * 100 if resume_word_count > 0 else 0
            keyword_density[keyword] = round(density, 2)
        
        return keyword_density

    async def _generate_improvement_suggestions(self, resume_content: Dict[str, Any], job_description: JobDescription, missing_skills: List[str]) -> List[str]:
        """Generate AI-powered improvement suggestions"""
        try:
            prompt = f"""
            Analyze this resume against the job description and provide specific improvement suggestions.
            
            Job Title: {job_description.title}
            Company: {job_description.company}
            
            Job Requirements:
            {' '.join(job_description.requirements)}
            
            Required Skills:
            {' '.join(job_description.skills_required)}
            
            Resume Summary:
            {json.dumps(resume_content, indent=2)}
            
            Missing Skills: {', '.join(missing_skills)}
            
            Provide 5 specific, actionable suggestions to improve this resume for this job:
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            suggestions_text = response.choices[0].message.content
            suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip() and not s.strip().isdigit()]
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating improvement suggestions: {str(e)}")
            return ["Unable to generate suggestions at this time."]

    async def _generate_customized_resume(self, resume_content: Dict[str, Any], job_description: JobDescription, customization_level: str, analysis: ResumeAnalysis) -> Dict[str, Any]:
        """Generate AI-customized resume content"""
        try:
            customization_instructions = {
                "light": "Make minimal changes, focus on keyword optimization and summary adjustment",
                "moderate": "Make moderate changes including rephrasing experience descriptions and optimizing skills",
                "heavy": "Make significant changes including restructuring content and adding relevant details"
            }
            
            prompt = f"""
            Customize this resume for the following job opportunity. 
            Customization Level: {customization_level} - {customization_instructions[customization_level]}
            
            Job Title: {job_description.title}
            Company: {job_description.company}
            Job Description: {job_description.description}
            
            Required Skills: {', '.join(job_description.skills_required)}
            Requirements: {', '.join(job_description.requirements)}
            
            Current Resume:
            {json.dumps(resume_content, indent=2)}
            
            Current Match Score: {analysis.job_match_score:.1f}%
            Missing Skills: {', '.join(analysis.missing_skills)}
            
            Return the customized resume in the same JSON format, making improvements to increase job match while maintaining truthfulness. Focus on:
            1. Optimizing the professional summary
            2. Rephrasing experience descriptions to highlight relevant skills
            3. Reorganizing skills to prioritize job-relevant ones
            4. Adding relevant keywords naturally
            
            Return only the JSON object:
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.5
            )
            
            # Parse the response
            customized_text = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                json_start = customized_text.find('{')
                json_end = customized_text.rfind('}') + 1
                json_str = customized_text[json_start:json_end]
                
                customized_content = json.loads(json_str)
                return customized_content
                
            except json.JSONDecodeError:
                logger.error("Failed to parse AI response as JSON")
                return resume_content  # Return original if parsing fails
            
        except Exception as e:
            logger.error(f"Error generating customized resume: {str(e)}")
            return resume_content  # Return original resume if error occurs

    def _track_changes(self, original: Dict[str, Any], customized: Dict[str, Any]) -> List[str]:
        """Track changes made during customization"""
        changes = []
        
        # Check for changes in different sections
        if original.get('personal_info', {}).get('summary') != customized.get('personal_info', {}).get('summary'):
            changes.append("Updated professional summary")
        
        if original.get('skills') != customized.get('skills'):
            changes.append("Reorganized and optimized skills section")
        
        # Check experience descriptions
        orig_exp = original.get('experience', [])
        cust_exp = customized.get('experience', [])
        
        if len(orig_exp) == len(cust_exp):
            for i, (orig, cust) in enumerate(zip(orig_exp, cust_exp)):
                if orig.get('description') != cust.get('description'):
                    changes.append(f"Enhanced description for {orig.get('title', 'position')} role")
        
        if not changes:
            changes.append("Minor keyword and formatting optimizations")
        
        return changes

    async def _generate_customization_suggestions(self, customized_content: Dict[str, Any], job_description: JobDescription, analysis: ResumeAnalysis) -> List[str]:
        """Generate suggestions for further improvement after customization"""
        suggestions = [
            "Review and verify all customized content for accuracy",
            "Consider adding specific metrics and achievements",
            "Tailor your cover letter to complement the customized resume"
        ]
        
        if analysis.job_match_score < 70:
            suggestions.append("Consider gaining experience in missing key skills")
        
        if len(analysis.missing_skills) > 3:
            suggestions.append("Focus on developing the most critical missing skills")
        
        return suggestions

# Initialize AI service
ai_service = AIService()