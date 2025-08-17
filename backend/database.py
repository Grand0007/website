from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, Boolean, Integer, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from databases import Database
import os
from datetime import datetime
import uuid
from typing import Optional

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_resume.db")

# Create database instance
database = Database(DATABASE_URL)
metadata = MetaData()

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Tables
users_table = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("first_name", String, nullable=False),
    Column("last_name", String, nullable=False),
    Column("role", String, default="user"),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, onupdate=datetime.utcnow),
)

resumes_table = Table(
    "resumes",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("user_id", String, ForeignKey("users.id"), nullable=False),
    Column("title", String, nullable=False),
    Column("file_name", String, nullable=False),
    Column("file_path", String, nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("content", JSON),
    Column("skills", JSON),
    Column("experience", JSON),
    Column("education", JSON),
    Column("status", String, default="uploaded"),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, onupdate=datetime.utcnow),
)

otp_codes_table = Table(
    "otp_codes",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("email", String, nullable=False),
    Column("code", String, nullable=False),
    Column("expires_at", DateTime, nullable=False),
    Column("is_used", Boolean, default=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

ai_processing_logs_table = Table(
    "ai_processing_logs",
    metadata,
    Column("id", String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column("resume_id", String, ForeignKey("resumes.id"), nullable=False),
    Column("job_description", JSON, nullable=False),
    Column("customization_level", String, nullable=False),
    Column("match_score", Float),
    Column("processing_time", Float),
    Column("changes_made", JSON),
    Column("suggestions", JSON),
    Column("status", String, default="processing"),
    Column("error_message", String),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content = Column(JSON)
    skills = Column(JSON)
    experience = Column(JSON)
    education = Column(JSON)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class OTPCode(Base):
    __tablename__ = "otp_codes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False)
    code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AIProcessingLog(Base):
    __tablename__ = "ai_processing_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)
    job_description = Column(JSON, nullable=False)
    customization_level = Column(String, nullable=False)
    match_score = Column(Float)
    processing_time = Column(Float)
    changes_made = Column(JSON)
    suggestions = Column(JSON)
    status = Column(String, default="processing")
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database dependency
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database utilities
class DatabaseManager:
    def __init__(self):
        self.database = database
    
    async def connect(self):
        await self.database.connect()
    
    async def disconnect(self):
        await self.database.disconnect()
    
    async def execute_query(self, query, values=None):
        if values:
            return await self.database.execute(query, values)
        return await self.database.execute(query)
    
    async def fetch_one(self, query, values=None):
        if values:
            return await self.database.fetch_one(query, values)
        return await self.database.fetch_one(query)
    
    async def fetch_all(self, query, values=None):
        if values:
            return await self.database.fetch_all(query, values)
        return await self.database.fetch_all(query)

# Initialize database manager
db_manager = DatabaseManager()