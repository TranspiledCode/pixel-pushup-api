# backend/config.py
import os

class Config:
    """Base configuration."""
    VERBOSE = os.environ.get('VERBOSE', 'False').lower() in ['true', '1', 'yes']
    LOG_LEVEL = 'DEBUG' if VERBOSE else 'INFO'
    
    # Additional configurations can be added here
    # For example:
    # AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
    # SUPPORTED_EXPORT_TYPES = ['png', 'webp', 'jpg', 'jpeg']
