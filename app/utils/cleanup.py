import logging
from sqlalchemy.orm import Session
from ..models import File, FileVersion, FileShare
from .s3_service import S3Service
from ..database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_storage():
    """Clean up all files and folders from S3 and database"""
    try:
        # Initialize S3 service
        s3_service = S3Service()
        
        # Get database session
        db = next(get_db())
        
        # Delete all files from S3
        logger.info("Deleting all files from S3...")
        files = db.query(File).all()
        for file in files:
            try:
                # Delete all versions of the file from S3
                versions = db.query(FileVersion).filter(FileVersion.file_id == file.id).all()
                for version in versions:
                    if version.file_path:
                        s3_service.delete_file(version.file_path)
                        logger.info(f"Deleted version from S3: {version.file_path}")
                
                # Delete the current version from S3
                if file.file_path:
                    s3_service.delete_file(file.file_path)
                    logger.info(f"Deleted file from S3: {file.file_path}")
            except Exception as e:
                logger.error(f"Error deleting file from S3: {str(e)}")
        
        # Delete all records from database
        logger.info("Deleting all records from database...")
        db.query(FileShare).delete()
        db.query(FileVersion).delete()
        db.query(File).delete()
        db.commit()
        
        logger.info("Cleanup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return False

if __name__ == "__main__":
    cleanup_storage() 