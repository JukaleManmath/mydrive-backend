import os
import mimetypes
import logging
from fastapi import UploadFile
from datetime import datetime
from .utils.s3_service import S3Service

# Configure logging
logger = logging.getLogger(__name__)

# Initialize S3 service
s3_service = S3Service()

# Allowed file types
ALLOWED_TYPES = {
    # Images
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    # Text files
    'text/plain', 'text/csv', 'text/html', 'text/css', 'text/javascript',
    'application/json', 'application/xml',
    # Code files
    'application/x-python', 'text/x-python', 'text/python',
    'text/x-python-script', 'text/x-python3', 'text/x-python3-script',
    'application/x-python-script', 'application/x-python3',
    'text/x-java', 'text/java',
    'text/x-c++', 'text/c++',
    'text/x-c', 'text/c',
    'text/x-php', 'text/php',
    'text/x-ruby', 'text/ruby',
    'text/x-swift', 'text/swift',
    'text/x-typescript', 'text/typescript',
    'text/x-javascript', 'text/javascript',
    'text/x-jsx', 'text/jsx',
    'text/x-tsx', 'text/tsx',
    'text/x-go', 'text/go',
    'text/x-rust', 'text/rust',
    'text/x-kotlin', 'text/kotlin',
    'text/x-scala', 'text/scala',
    'text/x-haskell', 'text/haskell',
    'text/x-lua', 'text/lua',
    'text/x-perl', 'text/perl',
    'text/x-shell', 'text/shell',
    'text/x-bash', 'text/bash',
    'text/x-yaml', 'text/yaml',
    'text/x-toml', 'text/toml',
    'text/x-markdown', 'text/markdown',
    'text/x-dockerfile', 'text/dockerfile',
    # Spreadsheets
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

def get_file_type(file_path: str) -> str:
    """Get the MIME type of a file"""
    return mimetypes.guess_type(file_path)[0]

def is_valid_file_type(file_type: str) -> bool:
    """Check if the file type is allowed"""
    return file_type in ALLOWED_TYPES

def save_upload_file(file: UploadFile, user_id: int) -> tuple[str, int, str]:
    """Save uploaded file to S3 and return (file_path, file_size, file_type)"""
    try:
        logger.info(f"Starting file save for user {user_id}")
    
    # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        # Get file type
        file_type = file.content_type or 'application/octet-stream'
        if not is_valid_file_type(file_type):
            raise ValueError(f"Invalid file type: {file_type}")
        
        # Upload to S3
        s3_key = s3_service.upload_file(file.file, file.filename, str(user_id))
        logger.info(f"File uploaded to S3 with key: {s3_key}")
        
        return s3_key, file_size, file_type
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise e

def delete_file(file_path: str) -> bool:
    """Delete a file from S3"""
    try:
        s3_service.delete_file(file_path)
        return True
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False

def get_file_size(file_path: str) -> int:
    """Get file size in bytes from S3"""
    try:
        return s3_service.get_file_size(file_path)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return 0 