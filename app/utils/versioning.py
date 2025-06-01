import os
import shutil
from datetime import datetime
from typing import Optional
from ..models import FileVersion, File
from sqlalchemy.orm import Session

def create_version(
    db: Session,
    file: File,
    user_id: int,
    comment: Optional[str] = None
) -> FileVersion:
    """
    Create a new version of a file.
    """
    try:
    # Get the latest version number
    latest_version = db.query(FileVersion)\
        .filter(FileVersion.file_id == file.id)\
        .order_by(FileVersion.version_number.desc())\
        .first()
    
        # Set the new version number
        new_version_number = 1 if latest_version is None else latest_version.version_number + 1
    
    # Create version directory if it doesn't exist
        version_dir = os.path.join(os.path.dirname(file.file_path), 'versions')
        if not os.path.exists(version_dir):
            os.makedirs(version_dir)
    
        # Create the version path
        version_path = os.path.join(version_dir, f'v{new_version_number}_{os.path.basename(file.file_path)}')
        
        # Read the current file content
        with open(file.file_path, 'rb') as src_file:
            content = src_file.read()
    
        # Write the content to the version file
        with open(version_path, 'wb') as dst_file:
            dst_file.write(content)
    
        # Create the version record
        version = FileVersion(
        file_id=file.id,
        file_path=version_path,
            created_at=datetime.utcnow(),
        created_by=user_id,
            version_number=new_version_number,
            file_size=len(content),
        comment=comment,
        is_current=True
    )
    
        # Mark all other versions as not current
        db.query(FileVersion)\
            .filter(FileVersion.file_id == file.id)\
            .update({"is_current": False})
        
        db.add(version)
    db.commit()
        db.refresh(version)
    
        return version
    except Exception as e:
        db.rollback()
        raise e

def restore_version(
    db: Session,
    version: FileVersion,
    user_id: int
) -> FileVersion:
    """
    Restore a file to a previous version.
    """
    try:
    file = version.file
        
        # Copy the restored version's content to the current file
        shutil.copy2(version.file_path, file.file_path)
    
    # Create a new version from the restored version
    new_version = create_version(
        db=db,
        file=file,
        user_id=user_id,
        comment=f"Restored from version {version.version_number}"
    )
    
    return new_version
    except Exception as e:
        db.rollback()
        raise e

def delete_version(db: Session, file: File, version_number: int) -> None:
    """
    Delete a specific version of a file.
    
    Args:
        db: Database session
        file: File model instance
        version_number: Version number to delete
        
    Raises:
        ValueError: If version is current or not found
    """
    # Get the version
    version = db.query(FileVersion).filter(
        FileVersion.file_id == file.id,
        FileVersion.version_number == version_number
    ).first()
    
    if not version:
        raise ValueError("Version not found")
        
    # Get the latest version number for this file
    latest_version = db.query(FileVersion).filter(
        FileVersion.file_id == file.id
    ).order_by(FileVersion.version_number.desc()).first()
    if latest_version and version.version_number == latest_version.version_number:
        raise ValueError("Cannot delete the current version of a file")
    
    try:
        # Delete the version file if it exists
        if version.file_path and os.path.exists(version.file_path):
        os.remove(version.file_path)
    
    # Delete the version record
    db.delete(version)
    db.commit()
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error deleting version: {str(e)}")

def get_version_history(
    db: Session,
    file_id: int
) -> list[FileVersion]:
    """
    Get the version history of a file.
    """
    return db.query(FileVersion)\
        .filter(FileVersion.file_id == file_id)\
        .order_by(FileVersion.version_number.desc())\
        .all() 