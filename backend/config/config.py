import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database Configuration - MUST be set via environment variables
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable is required")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Configuration - MUST be set via environment variables
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    # JWT Configuration - More secure settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", "24")))  # Default 2 hours
    JWT_ALGORITHM = "HS256"
    JWT_DECODE_AUDIENCE = None
    JWT_ENCODE_AUDIENCE = None
    JWT_ERROR_MESSAGE_KEY = "message"
    
    # Environment-specific CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Security settings
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
