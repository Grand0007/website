import os
import smtplib
import random
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import get_db, users_table, otp_codes_table, db_manager
from models.schemas import User, UserCreate, Token, OTPRequest, OTPVerify
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Email configuration
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL")

    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join(random.choices(string.digits, k=length))

    async def send_otp_email(self, email: str, otp_code: str) -> bool:
        """Send OTP code via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "Your AI Resume Updater Login Code"

            body = f"""
            <html>
                <body>
                    <h2>Your Login Code</h2>
                    <p>Your verification code is: <strong style="font-size: 24px; color: #007bff;">{otp_code}</strong></p>
                    <p>This code will expire in 10 minutes.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                    <br>
                    <p>Best regards,<br>AI Resume Updater Team</p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"OTP email sent successfully to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return False

    async def create_otp(self, email: str) -> Dict[str, Any]:
        """Create and store OTP for email authentication"""
        try:
            # Generate OTP
            otp_code = self.generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            
            # Store OTP in database
            query = otp_codes_table.insert().values(
                email=email,
                code=otp_code,
                expires_at=expires_at,
                is_used=False
            )
            
            await db_manager.execute_query(query)
            
            # Send OTP via email
            email_sent = await self.send_otp_email(email, otp_code)
            
            if not email_sent:
                raise Exception("Failed to send OTP email")
            
            return {
                "success": True,
                "message": "OTP sent successfully",
                "expires_in": 600  # 10 minutes in seconds
            }
            
        except Exception as e:
            logger.error(f"Error creating OTP for {email}: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send OTP",
                "error": str(e)
            }

    async def verify_otp(self, email: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP code and authenticate user"""
        try:
            # Find valid OTP
            query = f"""
                SELECT * FROM otp_codes 
                WHERE email = :email 
                AND code = :code 
                AND expires_at > :now 
                AND is_used = false 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            
            otp_record = await db_manager.fetch_one(
                query, 
                {
                    "email": email, 
                    "code": otp_code, 
                    "now": datetime.utcnow()
                }
            )
            
            if not otp_record:
                return {
                    "success": False,
                    "message": "Invalid or expired OTP code"
                }
            
            # Mark OTP as used
            update_query = f"""
                UPDATE otp_codes 
                SET is_used = true 
                WHERE id = :otp_id
            """
            await db_manager.execute_query(update_query, {"otp_id": otp_record["id"]})
            
            # Get or create user
            user = await self.get_or_create_user(email)
            
            # Generate access token
            token = self.create_access_token({"sub": user["email"]})
            
            return {
                "success": True,
                "message": "Authentication successful",
                "token": token,
                "user": user
            }
            
        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {str(e)}")
            return {
                "success": False,
                "message": "Authentication failed",
                "error": str(e)
            }

    async def get_or_create_user(self, email: str) -> Dict[str, Any]:
        """Get existing user or create new one"""
        try:
            # Check if user exists
            query = "SELECT * FROM users WHERE email = :email"
            user = await db_manager.fetch_one(query, {"email": email})
            
            if user:
                return dict(user)
            
            # Create new user
            first_name, last_name = self.parse_name_from_email(email)
            
            insert_query = users_table.insert().values(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role="user",
                is_active=True
            )
            
            user_id = await db_manager.execute_query(insert_query)
            
            # Fetch the created user
            user = await db_manager.fetch_one(
                "SELECT * FROM users WHERE email = :email", 
                {"email": email}
            )
            
            logger.info(f"New user created: {email}")
            return dict(user)
            
        except Exception as e:
            logger.error(f"Error getting/creating user {email}: {str(e)}")
            raise

    def parse_name_from_email(self, email: str) -> tuple:
        """Extract first and last name from email"""
        username = email.split('@')[0]
        name_parts = username.replace('.', ' ').replace('_', ' ').split()
        
        if len(name_parts) >= 2:
            return name_parts[0].title(), ' '.join(name_parts[1:]).title()
        else:
            return name_parts[0].title(), "User"

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": int(expires_delta.total_seconds()) if expires_delta else self.access_token_expire_minutes * 60
        }

    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str = payload.get("sub")
            
            if email is None:
                return None
            
            # Get user from database
            query = "SELECT * FROM users WHERE email = :email AND is_active = true"
            user = await db_manager.fetch_one(query, {"email": email})
            
            return dict(user) if user else None
            
        except jwt.PyJWTError:
            return None

    async def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        return await self.verify_token(token)

    async def cleanup_expired_otps(self):
        """Clean up expired OTP codes"""
        try:
            query = "DELETE FROM otp_codes WHERE expires_at < :now"
            await db_manager.execute_query(query, {"now": datetime.utcnow()})
            logger.info("Expired OTP codes cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up expired OTPs: {str(e)}")

# Initialize auth service
auth_service = AuthService()