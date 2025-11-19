import os
from datetime import timedelta

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///bharatpay.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Secret
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'bharatpay-super-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Admin Credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')  # Change this!
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = "memory://"
    
    # CORS
    CORS_ORIGINS = ["*"]  # In production, specify exact domains
