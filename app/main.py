from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os
import logging
from datetime import timedelta, datetime
from pydantic import BaseModel
import shutil
from . import models, schemas, crud
from .database import engine, get_db
from .utils import versioning
from .utils.s3_service import S3Service
from .auth.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user
)
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text  # Add this import at the top with other imports
import io
from fastapi.responses import StreamingResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize S3 service
s3_service = S3Service()

app = FastAPI(title="MyDrive")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://mydrive-frontend.vercel.app",  # Production frontend
        "https://mydrive-frontend-git-main-jukalemanmath.vercel.app",  # Vercel preview
        "https://mydrive-frontend-jukalemanmath.vercel.app",  # Vercel production
        os.getenv("CORS_ORIGINS", "").split(",")  # Additional origins from env
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Mount static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response

# Authentication routes
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=schemas.User)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Registration attempt for user: {user.username}")
        
        # Validate email format
        if not user.email or '@' not in user.email:
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Validate username
        if not user.username or len(user.username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters long")
        
        # Validate password
        if not user.password or len(user.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
        
        # Check if email exists
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username exists
        db_user = db.query(models.User).filter(models.User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User registered successfully: {user.username}")
        return db_user
        
    except HTTPException as he:
        logger.error(f"Registration error: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Recursive helper function to convert SQLAlchemy File model to dictionary
def file_to_dict(file_obj: models.File):
    if file_obj is None:
        return None
        
    # Start with basic attributes
    file_dict = {
        "id": file_obj.id,
        "filename": file_obj.filename,
        "file_path": file_obj.file_path,
        "file_size": file_obj.file_size,
        "file_type": file_obj.file_type,
        "upload_date": file_obj.upload_date,
        "owner_id": file_obj.owner_id,
        "parent_id": file_obj.parent_id,
        "type": 'folder' if (getattr(file_obj, 'mime_type', None) == 'folder' or getattr(file_obj, 'file_type', None) == 'folder' or getattr(file_obj, 'type', None) == 'folder') else 'file',
        "is_folder": (getattr(file_obj, 'mime_type', None) == 'folder' or getattr(file_obj, 'file_type', None) == 'folder' or getattr(file_obj, 'type', None) == 'folder'),
        "is_shared": file_obj.is_shared,
        "name": file_obj.filename,  # Add name field for frontend
        "size": file_obj.file_size,  # Add size field for frontend
        "s3_key": file_obj.file_path or "",  # Use empty string if file_path is None
    }
    
    # Add optional fields if they exist
    if hasattr(file_obj, 'created_at'):
        file_dict["created_at"] = file_obj.created_at
    if hasattr(file_obj, 'updated_at'):
        file_dict["updated_at"] = file_obj.updated_at
    if hasattr(file_obj, 'is_deleted'):
        file_dict["is_deleted"] = file_obj.is_deleted
    if hasattr(file_obj, 'version'):
        file_dict["version"] = file_obj.version
    if hasattr(file_obj, 'mime_type'):
        file_dict["mime_type"] = file_obj.mime_type
    
    # Recursively convert children if they exist
    children_list = []
    # Check if children relationship is loaded and is an iterable
    if hasattr(file_obj, 'children') and isinstance(file_obj.children, (list, tuple)):
        for child_item in file_obj.children:
            children_list.append(file_to_dict(child_item))
    # Ensure children key is always a list
    file_dict["children"] = children_list
    
    return file_dict

# File operations
@app.post("/files/upload", response_model=schemas.File, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    parent_id: Optional[int] = Form(None),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Starting file upload for user {current_user.username}")
        logger.info(f"File details: filename={file.filename}, content_type={file.content_type}")
        
        if parent_id is not None:
            logger.info(f"Checking parent folder with ID: {parent_id}")
            parent_folder = db.query(models.File).filter(
                models.File.id == parent_id,
                models.File.owner_id == current_user.id,
                models.File.type == 'folder'
            ).first()
            if not parent_folder:
                logger.error(f"Parent folder not found or not owned by user: {parent_id}")
                raise HTTPException(status_code=404, detail="Parent folder not found or not owned by user")

        # Get file size before uploading
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        # Get file type
        file_type = file.content_type or 'application/octet-stream'
        
        # Upload file to S3
        logger.info("Uploading file to S3...")
        try:
            s3_key = s3_service.upload_file(file.file, file.filename, str(current_user.id))
            logger.info(f"File uploaded to S3 with key: {s3_key}")
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error uploading file to S3: {str(e)}")
        
        logger.info("Creating database record...")
        try:
            db_file = models.File(
                filename=file.filename,
                file_path=s3_key,  # Store S3 key as file_path
                file_size=file_size,
                file_type=file_type,
                upload_date=datetime.utcnow(),
                owner_id=current_user.id,
                parent_id=parent_id,
                type='file',
                mime_type=file_type
            )
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            logger.info(f"Database record created with ID: {db_file.id}")
        except Exception as e:
            logger.error(f"Error creating database record: {str(e)}")
            # Try to clean up the S3 file if database operation fails
            try:
                s3_service.delete_file(s3_key)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up S3 file after database failure: {str(cleanup_error)}")
            raise HTTPException(status_code=500, detail=f"Error creating file record: {str(e)}")

        # After successful upload, create initial version using raw SQL
        if db_file.type == 'file':
            logger.info("Creating initial version...")
            try:
                # Use raw SQL to avoid model issues
                create_version = text("""
                    INSERT INTO file_versions 
                    (file_id, version_number, file_path, file_size, created_at) 
                    VALUES 
                    (:file_id, :version_number, :file_path, :file_size, :created_at)
                """)
                db.execute(create_version, {
                    "file_id": db_file.id,
                    "version_number": 1,
                    "file_path": db_file.file_path,
                    "file_size": db_file.file_size,
                    "created_at": db_file.upload_date
                })
                db.commit()
                logger.info(f"Created initial version for file: {db_file.id}")
            except Exception as e:
                logger.error(f"Error creating version: {str(e)}")
                # Continue even if version creation fails

        # Convert the newly created SQLAlchemy file object to a dictionary
        result = file_to_dict(db_file)
        logger.info("File upload completed successfully")
        return result
        
    except HTTPException as he:
        logger.error(f"HTTP Exception during file upload: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during file upload: {str(e)}")

def get_folder_contents(db: Session, folder_id: int, current_user_id: int):
    """Get all files in a folder that are shared with the user."""
    contents = []
    # Get all children of the folder
    children = db.query(models.File).filter(models.File.parent_id == folder_id).all()
    
    for child in children:
        # Only process files, not folders
        if child.type == 'file':
            # Check if this file is shared with the user
            share = db.query(models.FileShare).filter(
                models.FileShare.file_id == child.id,
                models.FileShare.shared_with_id == current_user_id
            ).first()
            
            # If the file is shared or if it's in a shared folder
            if share or child.parent_id == folder_id:
                file_dict = {
                    "id": child.id,
                    "filename": child.filename,
                    "file_path": child.file_path,
                    "file_size": child.file_size,
                    "file_type": child.file_type,
                    "upload_date": child.upload_date.isoformat() if child.upload_date else None,
                    "owner_id": child.owner_id,
                    "is_shared": True,  # Mark as shared since it's in a shared folder
                    "type": child.type,
                    "parent_id": child.parent_id,
                    "permission": share.permission if share else 'read',  # Use share permission or default to read
                    "children": []
                }
                contents.append(file_dict)
    
    return contents

@app.get("/files/shared-with-me", response_model=List[schemas.FileShare])
def files_shared_with_me(
    current_user: models.User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get files shared with the current user"""
    logger.info(f"Fetching shared files for user: {current_user.email} (ID: {current_user.id})")
    try:
        # First try with share_date
        return db.query(models.FileShare).filter(
            models.FileShare.shared_with_id == current_user.id
        ).order_by(models.FileShare.share_date.desc()).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Error fetching shared files: {str(e)}")
        # If share_date column doesn't exist, try without it
        return db.query(models.FileShare).filter(
            models.FileShare.shared_with_id == current_user.id
        ).offset(skip).limit(limit).all()

@app.get("/files/recent-shared", response_model=List[schemas.FileShare])
def recent_shared_files(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get recently shared files"""
    logger.info(f"Fetching recent shared files for user: {current_user.email}")
    try:
        # First try with share_date
        return db.query(models.FileShare).filter(
            models.FileShare.shared_with_id == current_user.id,
            models.FileShare.file_id.isnot(None)
        ).order_by(models.FileShare.share_date.desc()).limit(3).all()
    except Exception as e:
        logger.error(f"Error fetching recent shared files: {str(e)}")
        # If share_date column doesn't exist, try without it
        return db.query(models.FileShare).filter(
            models.FileShare.shared_with_id == current_user.id,
            models.FileShare.file_id.isnot(None)
        ).limit(3).all()

@app.get("/files/", response_model=List[schemas.File])
def get_files(
    parent_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.File).filter(models.File.owner_id == current_user.id)
    if parent_id is not None:
        query = query.filter(models.File.parent_id == parent_id)
    else:
        query = query.filter(models.File.parent_id.is_(None))
    files = [file_to_dict(file) for file in query.all()]
    logger.info(f"Returning files: {files}")
    return files

@app.get("/files/all", response_model=List[schemas.File])
def get_all_files(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all files and folders owned by the user, regardless of their location in the folder structure."""
    try:
        query = db.query(models.File).filter(models.File.owner_id == current_user.id)
        return [file_to_dict(file) for file in query.all()]
    except Exception as e:
        logger.error(f"Error fetching all files: {str(e)}")
        # If created_at/updated_at columns don't exist, try without them
        query = db.query(
            models.File.id,
            models.File.filename,
            models.File.file_path,
            models.File.file_size,
            models.File.file_type,
            models.File.upload_date,
            models.File.owner_id,
            models.File.is_shared,
            models.File.type,
            models.File.parent_id,
            models.File.is_deleted,
            models.File.version,
            models.File.mime_type
        ).filter(models.File.owner_id == current_user.id)
        return [file_to_dict(file) for file in query.all()]

@app.get("/files/{file_id}", response_model=schemas.File)
def get_file(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access to the file
    if file.owner_id != current_user.id and not file.is_shared:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    
    # For folders, we don't need to check the file path, return the dictionary representation
    if file.type == 'folder':
        return file_to_dict(file)
    
    # For files, verify the file exists
    if not file.file_path or not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return file

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Delete request for file ID: {file_id} from user: {current_user.username}")
        
        # Get the file
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user is the owner
        if file.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")
        
        # Delete the file from S3 if it's a file (not a folder)
        if file.type == 'file' and file.file_path:
            try:
                logger.info(f"Deleting file from S3: {file.file_path}")
                s3_service.delete_file(file.file_path)
                logger.info("File deleted from S3 successfully")
            except Exception as e:
                logger.error(f"Error deleting file from S3: {str(e)}")
                # Continue with database deletion even if S3 deletion fails
        
        # Delete all shares first
        try:
            delete_shares = text("DELETE FROM file_shares WHERE file_id = :file_id")
            db.execute(delete_shares, {"file_id": file_id})
            db.commit()
            logger.info(f"Deleted shares for file {file_id}")
        except Exception as e:
            logger.error(f"Error deleting shares: {str(e)}")
            db.rollback()
        
        # Delete the file record
        try:
            # First, try to delete any versions
            try:
                delete_versions = text("DELETE FROM file_versions WHERE file_id = :file_id")
                db.execute(delete_versions, {"file_id": file_id})
                db.commit()
                logger.info(f"Deleted versions for file {file_id}")
            except Exception as e:
                logger.error(f"Error deleting versions: {str(e)}")
                db.rollback()
                # Continue with file deletion even if version deletion fails
            
            # Then delete the file using raw SQL
            try:
                delete_file = text("DELETE FROM files WHERE id = :file_id")
                db.execute(delete_file, {"file_id": file_id})
                db.commit()
                logger.info(f"File {file_id} deleted successfully")
                return {"message": "File deleted successfully"}
            except Exception as e:
                logger.error(f"Error deleting file record: {str(e)}")
                db.rollback()
                raise HTTPException(status_code=500, detail=str(e))
            
        except Exception as e:
            logger.error(f"Error in file deletion process: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def recursively_share_folder(db: Session, folder_id: int, shared_with_id: int, permission: str):
    """Share all files in a folder with a user, but not subfolders."""
    logger.info(f"Sharing contents of folder ID: {folder_id} with user ID: {shared_with_id}")
    
    # Get all files and subfolders in this folder
    children = db.query(models.File).filter(models.File.parent_id == folder_id).all()
    logger.info(f"Found {len(children)} items in folder {folder_id}")
    
    for child in children:
        # Only create share entry for files, not folders
        if child.type == 'file':
            logger.info(f"Sharing file: {child.filename} (ID: {child.id})")
            # Create share entry for this file
            share = models.FileShare(
                file_id=child.id,
                shared_with_id=shared_with_id,
                permission=permission
            )
            db.add(share)
            child.is_shared = True
        else:
            logger.info(f"Skipping subfolder: {child.filename} (ID: {child.id})")
    
    db.commit()
    logger.info(f"Finished sharing contents of folder {folder_id}")

@app.post("/files/{file_id}/share")
def share_file(
    file_id: int,
    share_data: schemas.FileShareCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Share request for file/folder ID: {file_id} from user: {current_user.username}")
        # Get the file/folder to share
        item = db.query(models.File).filter(models.File.id == file_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="File or folder not found")
        logger.info(f"Found item: {item.filename} (ID: {item.id}, type: {item.type})")
        # Check if user is the owner
        if item.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to share this item")
        # Get the user to share with by email
        shared_with_user = db.query(models.User).filter(models.User.email == share_data.shared_with_email).first()
        if not shared_with_user:
            raise HTTPException(status_code=404, detail="User not found")
        # Check if already shared
        existing_share = db.query(models.FileShare).filter(
            models.FileShare.file_id == file_id,
            models.FileShare.shared_with_id == shared_with_user.id
        ).first()
        if existing_share:
            # Update existing share
            existing_share.permission = share_data.permission
            db.commit()
            logger.info(f"Updated share for {item.filename} with user {shared_with_user.email}")
            return {
                "file_id": file_id,
                "shared_with": shared_with_user.email,
                "permission": share_data.permission
            }
        # Create new share
        share = models.FileShare(
            file_id=file_id,
            shared_with_id=shared_with_user.id,
            permission=share_data.permission
        )
        db.add(share)
        # If it's a folder, recursively share all contents
        if item.type == 'folder':
            recursively_share_folder(db, file_id, shared_with_user.id, share_data.permission)
        db.commit()
        logger.info(f"Successfully shared {item.filename} with user {shared_with_user.email}")
        return {
            "file_id": file_id,
            "shared_with": shared_with_user.email,
            "permission": share_data.permission
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error sharing file/folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/folders/", response_model=schemas.File)
def create_folder(
    folder_data: schemas.FolderCreate,  # Use the FolderCreate schema
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Creating folder: {folder_data.name} for user {current_user.username}")
        
        # Check if parent folder exists and is owned by user
        if folder_data.parent_id is not None:
            parent_folder = db.query(models.File).filter(
                models.File.id == folder_data.parent_id,
                models.File.owner_id == current_user.id,
                models.File.type == 'folder'
            ).first()
            if not parent_folder:
                raise HTTPException(status_code=404, detail="Parent folder not found or not owned by user")

        # Create folder record with explicit type='folder'
        db_folder = models.File(
            filename=folder_data.name,  # Use the name from FolderCreate schema
            file_path=None,  # Folders don't have a file path
            file_size=0,  # Folders don't have a size
            file_type='folder',  # Set file_type to 'folder'
            upload_date=datetime.utcnow(),
            owner_id=current_user.id,
            parent_id=folder_data.parent_id,
            type='folder',  # Explicitly set type to folder
            is_shared=False,
            mime_type='folder'  # Set mime_type to 'folder'
        )
        db.add(db_folder)
        db.commit()
        db.refresh(db_folder)
        
        logger.info(f"Folder created successfully with ID: {db_folder.id}")
        return file_to_dict(db_folder)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{folder_id}/contents", response_model=List[schemas.File])
def get_folder_contents_endpoint(
    folder_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # First check if the folder exists and user has access
    folder = db.query(models.File).filter(
        models.File.id == folder_id,
        models.File.type == 'folder'
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Check if user has access to the folder
    if folder.owner_id != current_user.id:
        # Check if folder is shared with user
        share = db.query(models.FileShare).filter(
            models.FileShare.file_id == folder_id,
            models.FileShare.shared_with_id == current_user.id
        ).first()
        if not share:
            raise HTTPException(status_code=403, detail="Not authorized to access this folder")
    
    # Get all files and subfolders in the folder
    contents = db.query(models.File).filter(
        models.File.parent_id == folder_id
    ).all()
    
    return [file_to_dict(item) for item in contents]

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """Get current user profile with username"""
    try:
        # Ensure we have the latest data
        db = next(get_db())
        user = db.query(models.User).filter(models.User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Return user data with all required fields
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at if hasattr(user, 'created_at') else datetime.utcnow(),
            "updated_at": user.updated_at if hasattr(user, 'updated_at') else datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Welcome to MyDrive API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/files/", response_model=schemas.File)
def create_file(
    file: schemas.FileCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_file(db=db, file=file, user_id=current_user.id)

@app.get("/files/", response_model=list[schemas.File])
def read_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    files = crud.get_user_files(db, user_id=current_user.id, skip=skip, limit=limit)
    return files

@app.get("/files/{file_id}", response_model=schemas.File)
def read_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_file = crud.get_file(db, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if db_file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
    return db_file

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_file = crud.get_file(db, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if db_file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
    crud.delete_file(db=db, file_id=file_id)
    return {"message": "File deleted successfully"}

@app.post("/files/{file_id}/share", response_model=schemas.FileShare)
def share_file(
    file_id: int,
    share: schemas.FileShareCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_file = crud.get_file(db, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if db_file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to share this file")
    return crud.create_file_share(db=db, file_id=file_id, share=share)

@app.get("/shared-files/", response_model=list[schemas.File])
def read_shared_files(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    files = crud.get_shared_files(db, user_id=current_user.id, skip=skip, limit=limit)
    return files

@app.post("/files/{file_id}/versions", response_model=schemas.FileVersion)
def create_file_version(
    file_id: int,
    version: schemas.FileVersionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_file = crud.get_file(db, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if db_file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create version for this file")
    return crud.create_file_version(db=db, file_id=file_id, version=version, user_id=current_user.id)

@app.get("/files/{file_id}/versions", response_model=list[schemas.FileVersion])
def read_file_versions(
    file_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_file = crud.get_file(db, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=404, detail="File not found")
    if db_file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view versions of this file")
    versions = crud.get_file_versions(db, file_id=file_id, skip=skip, limit=limit)
    return versions

@app.patch("/users/me", response_model=schemas.User)
def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Check if email is being updated and if it's already taken
        if user_update.email and user_update.email != current_user.email:
            existing_user = db.query(models.User).filter(models.User.email == user_update.email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")

        # Check if username is being updated and if it's already taken
        if user_update.username and user_update.username != current_user.username:
            existing_user = db.query(models.User).filter(models.User.username == user_update.username).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")

        # Update user fields
        if user_update.email:
            current_user.email = user_update.email
        if user_update.username:
            current_user.username = user_update.username

        db.commit()
        db.refresh(current_user)
        return current_user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/content")
async def get_file_content(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get file content or presigned URL from S3"""
    try:
        # Get file from database
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        # Check if user has access
        if file.owner_id != current_user.id and not file.is_shared:
            raise HTTPException(status_code=403, detail="Not authorized to access this file")
        # Prevent preview for folders
        if file.type == 'folder' or (file.mime_type == 'folder'):
            raise HTTPException(status_code=400, detail="Cannot preview a folder")
        # If file is text or code, return content
        code_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.go', '.rs', '.swift', '.php', '.sh', '.pl', '.lua', '.md', '.json', '.yml', '.yaml', '.toml', '.ini', '.txt']
        ext = os.path.splitext(file.filename)[1].lower()
        is_code = ext in code_extensions
        is_text = (file.file_type and file.file_type.startswith('text/')) or (file.mime_type and file.mime_type.startswith('text/'))
        if is_text or is_code:
            try:
                file_content = s3_service.get_file(file.file_path)
                return {"content": file_content.decode('utf-8', errors='replace')}
            except Exception as e:
                logger.error(f"Error getting text/code file from S3: {str(e)}")
                raise HTTPException(status_code=500, detail="Error retrieving file")
        # For binary files (pdf, images, etc.), return a presigned URL
        try:
            url = s3_service.get_file_url(file.file_path)
            return {"url": url}
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise HTTPException(status_code=500, detail="Error retrieving file URL")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting file content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download a file from S3"""
    try:
        # Get file from database
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user has access
        if file.owner_id != current_user.id and not file.is_shared:
            raise HTTPException(status_code=403, detail="Not authorized to access this file")
        
        # Prevent download for folders
        if file.type == 'folder' or (file.mime_type == 'folder'):
            raise HTTPException(status_code=400, detail="Cannot download a folder")
        
        try:
            # Get file from S3
            file_content = s3_service.get_file(file.file_path)
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=file.file_type or 'application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="{file.filename}"'
                }
            )
        except Exception as e:
            logger.error(f"Error getting file from S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Error retrieving file")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/files/{file_id}/move")
async def move_file(
    file_id: int,
    move_data: schemas.FileMove,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Move a file or folder to a different parent folder"""
    try:
        # Get the file/folder to move
        item = db.query(models.File).filter(models.File.id == file_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="File or folder not found")
        
        # Check if user is the owner
        if item.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to move this item")
        
        # If moving to a folder, verify it exists and user has access
        if move_data.target_parent_id is not None:
            target_folder = db.query(models.File).filter(
                models.File.id == move_data.target_parent_id,
                models.File.type == 'folder'
            ).first()
            if not target_folder:
                raise HTTPException(status_code=404, detail="Target folder not found")
            
            # Prevent moving a folder into itself or its descendants
            if item.type == 'folder':
                current = target_folder
                while current is not None:
                    if current.id == item.id:
                        raise HTTPException(status_code=400, detail="Cannot move a folder into itself or its descendants")
                    current = current.parent
        
        # Update the parent_id
        item.parent_id = move_data.target_parent_id
        db.commit()
        db.refresh(item)
        
        return file_to_dict(item)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error moving file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Admin routes
@app.get("/admin/users", response_model=List[schemas.User])
def get_all_users(
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    try:
        users = db.query(models.User).all()
        return users
    except Exception as e:
        logger.error(f"Error getting all users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update a user (admin only)"""
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user fields
        for field, value in user_update.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)"""
    try:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Don't allow deleting the last admin
        if user.is_admin:
            admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
        
        db.delete(user)
        db.commit()
        return {"message": "User deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 