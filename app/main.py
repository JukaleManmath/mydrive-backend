from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request, Query, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os
import logging
from datetime import timedelta, datetime
from pydantic import BaseModel
import shutil
from . import models, schemas
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
        "type": file_obj.type,
        "is_shared": file_obj.is_shared,
    }
    
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
        
        if not file_utils.is_valid_file_type(file_type):
            logger.error(f"Invalid file type: {file_type}")
            raise HTTPException(status_code=400, detail="File type not allowed")

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
                type='file'
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

        # After successful upload, create initial version
        if db_file.type == 'file':
            logger.info("Creating initial version...")
            try:
                # Create initial version
                version = models.FileVersion(
                    file_id=db_file.id,
                    version_number=1,
                    file_path=db_file.file_path,
                    file_size=db_file.file_size,
                    created_at=db_file.upload_date
                )
                db.add(version)
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
    return [file_to_dict(file) for file in query.all()]

@app.get("/files/all", response_model=List[schemas.File])
def get_all_files(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all files and folders owned by the user, regardless of their location in the folder structure."""
    query = db.query(models.File).filter(models.File.owner_id == current_user.id)
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
        
        # Delete all versions
        versions = db.query(models.FileVersion).filter(models.FileVersion.file_id == file_id).all()
        for version in versions:
            if version.file_path:
                try:
                    s3_service.delete_file(version.file_path)
                except Exception as e:
                    logger.error(f"Error deleting version from S3: {str(e)}")
            db.delete(version)
        
        # Delete all shares
        shares = db.query(models.FileShare).filter(models.FileShare.file_id == file_id).all()
        for share in shares:
            db.delete(share)
        
        # Delete the file record
        db.delete(file)
        db.commit()
        
        logger.info(f"File {file_id} deleted successfully")
        return {"message": "File deleted successfully"}
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
        
        # Get the user to share with
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

@app.post("/folders/", response_model=schemas.File, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: schemas.FolderCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if parent_id is provided and valid
    if folder_data.parent_id is not None:
        parent_folder = db.query(models.File).filter(
            models.File.id == folder_data.parent_id,
            models.File.owner_id == current_user.id,
            models.File.type == 'folder'
        ).first()
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Parent folder not found or not owned by user")

    # Create the new folder entry
    db_folder = models.File(
        filename=folder_data.filename,
        owner_id=current_user.id,
        type='folder',
        parent_id=folder_data.parent_id,
        file_path=None,
        file_size=None,
        file_type=None,
        is_shared=False,
    )

    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)

    # Convert the newly created SQLAlchemy folder object to a dictionary
    # using the helper function before returning, to match the Pydantic schema.
    return file_to_dict(db_folder)

@app.patch("/files/{item_id}/move", response_model=schemas.File)
def move_item(
    item_id: int,
    move_data: schemas.MoveItem,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get the item to move
    item_to_move = db.query(models.File).filter(models.File.id == item_id).first()
    if not item_to_move:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check ownership
    if item_to_move.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to move this item")

    target_parent_id = move_data.target_parent_id

    # Validate the target parent folder
    if target_parent_id is not None:
        target_parent = db.query(models.File).filter(
            models.File.id == target_parent_id,
            models.File.owner_id == current_user.id,
            models.File.type == 'folder'
        ).first()
        if not target_parent:
            raise HTTPException(status_code=404, detail="Target parent folder not found or not owned by user")

        # Prevent moving an item into itself or its descendants
        # Check if target_parent is item_to_move or a descendant of item_to_move
        current = target_parent
        while current is not None:
            if current.id == item_to_move.id:
                raise HTTPException(status_code=400, detail="Cannot move an item into itself or a descendant")
            current = db.query(models.File).filter(models.File.id == current.parent_id).first()

    # Update the parent_id
    item_to_move.parent_id = target_parent_id
    db.commit()
    db.refresh(item_to_move)

    # Do not assign children manually; let SQLAlchemy/Pydantic handle it
    return file_to_dict(item_to_move)

# User Profile Endpoints
@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@app.patch("/users/me", response_model=schemas.User)
def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Update fields from user_update schema
    update_data = user_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        # Add validation or specific logic if needed for certain fields
        if field == "email":
            # Optional: Add email format validation here if not handled by Pydantic
            # Check if email already exists for another user
            existing_user = db.query(models.User).filter(models.User.email == value, models.User.id != current_user.id).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
        elif field == "username":
             # Optional: Add username validation here if not handled by Pydantic
            # Check if username already exists for another user
            existing_user = db.query(models.User).filter(models.User.username == value, models.User.id != current_user.id).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")

        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user

@app.patch("/users/me/password", response_model=schemas.User)
def update_user_password(
    password_update: schemas.PasswordUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Validate new password (e.g., minimum length)
    if len(password_update.new_password) < 6:
         raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")

    # Hash and update the password
    hashed_password = get_password_hash(password_update.new_password)
    current_user.hashed_password = hashed_password

    db.commit()
    db.refresh(current_user)
    return current_user

def is_file_accessible_by_shared_folder(db: Session, file: models.File, user_id: int) -> bool:
    """Check if a file is accessible because it's inside a folder that's shared with the user."""
    # Traverse up the parent chain to see if any ancestor is shared with the user
    current = file
    while current.parent_id is not None:
        parent = db.query(models.File).filter(models.File.id == current.parent_id).first()
        if not parent:
            break
        share = db.query(models.FileShare).filter(
            models.FileShare.file_id == parent.id,
            models.FileShare.shared_with_id == user_id
        ).first()
        if share:
            return True
        current = parent
    return False

@app.get("/files/{file_id}/content")
async def get_file_content(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Fetching content for file ID: {file_id} for user: {current_user.username}")
        
        # Get the file
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            logger.error(f"File not found with ID: {file_id}")
            raise HTTPException(status_code=404, detail="File not found")
        
        logger.info(f"Found file: {file.filename} (type: {file.file_type})")
        
        # Check if user has access to the file
        if file.owner_id != current_user.id:
            shared_file = db.query(models.FileShare).filter(
                models.FileShare.file_id == file_id,
                models.FileShare.shared_with_id == current_user.id
            ).first()
            if not shared_file:
                # Check if file is accessible via a shared folder
                if not is_file_accessible_by_shared_folder(db, file, current_user.id):
                    logger.error(f"Access denied for user {current_user.username} to file {file_id}")
                    raise HTTPException(status_code=403, detail="Access denied")
        
        if file.type == 'folder':
            raise HTTPException(status_code=400, detail="Cannot get content of a folder")
        
        if not file.file_path:
            raise HTTPException(status_code=404, detail="File path is missing")

        # Check if file exists in S3
        if not s3_service.file_exists(file.file_path):
            logger.error(f"File not found in S3: {file.file_path}")
            raise HTTPException(status_code=404, detail="File not found in storage")

        # For text-based files, return the content
        if file.file_type.startswith('text/') or file.file_type in [
            'application/json', 'application/xml',
            'application/x-python', 'text/x-python',
            'text/x-java', 'text/x-c++', 'text/x-c',
            'text/x-php', 'text/x-ruby', 'text/x-swift',
            'application/javascript', 'text/javascript',
            'text/css', 'text/html'
        ]:
            try:
                # Get the file content from S3
                logger.info(f"Downloading text file content from S3: {file.file_path}")
                content = s3_service.download_file(file.file_path)
                logger.info(f"Successfully read text file content for file {file_id}")
                return {"content": content.decode('utf-8')}
            except Exception as e:
                logger.error(f"Error reading text file content: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error reading file content: {str(e)}")
        else:
            # For binary files, return a URL to download the file
            try:
                # Get presigned URL for the file
                logger.info(f"Generating presigned URL for binary file: {file.file_path}")
                presigned_url = s3_service.get_file_url(file.file_path)
                logger.info(f"Generated presigned URL: {presigned_url}")
                return {
                    "url": presigned_url,
                    "filename": file.filename,
                    "content_type": file.file_type
                }
            except Exception as e:
                logger.error(f"Error generating download URL: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error generating download URL: {str(e)}")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in get_file_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Download request for file ID: {file_id} from user: {current_user.username}")
        
        # Get the file
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            logger.error(f"File not found with ID: {file_id}")
            raise HTTPException(status_code=404, detail="File not found")

        # Check if user has access to the file
        if file.owner_id != current_user.id:
            shared_file = db.query(models.FileShare).filter(
                models.FileShare.file_id == file_id,
                models.FileShare.shared_with_id == current_user.id
            ).first()
            if not shared_file:
                # Check if file is accessible via a shared folder
                if not is_file_accessible_by_shared_folder(db, file, current_user.id):
                    logger.error(f"Access denied for user {current_user.username} to file {file_id}")
                    raise HTTPException(status_code=403, detail="Access denied")

        # Get the file from S3
        if not file.file_path:
            logger.error(f"File path is missing for file ID: {file_id}")
            raise HTTPException(status_code=500, detail="File path is missing")

        try:
            # Get file content from S3
            content = s3_service.download_file(file.file_path)
            logger.info(f"Successfully downloaded file: {file_id}")
            
            # Return the file content with appropriate headers
            return Response(
                content=content,
                media_type=file.file_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{file.filename}"'
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting file from S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Error retrieving file from S3")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during file download: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/{file_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_file_version(
    file_id: int,
    file: UploadFile = File(...),
    comment: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new version of a file.
    """
    try:
        # Get the file
        file_obj = db.query(models.File).filter(models.File.id == file_id).first()
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user has permission
        if file_obj.owner_id != current_user.id:
            shared_file = db.query(models.FileShare).filter(
                models.FileShare.file_id == file_id,
                models.FileShare.shared_with_id == current_user.id,
                models.FileShare.permission == 'edit'
            ).first()
            if not shared_file:
                raise HTTPException(status_code=403, detail="Not authorized to create versions")
        
        # Read the new content
        file_content = await file.read()
        
        if not os.path.exists(file_obj.file_path):
            raise HTTPException(status_code=404, detail="Original file not found")
            
        try:
            # First create a new version with the current content
            version = versioning.create_version(db, file_obj, current_user.id, comment)
            
            # Then write the new content to the current file
            with open(file_obj.file_path, 'wb') as f:
                f.write(file_content)
            
            # Update the file size
            file_obj.file_size = len(file_content)
            db.commit()
            
            return version
        except Exception as e:
            # If anything fails, try to restore the original file
            if os.path.exists(file_obj.file_path + '.backup'):
                shutil.copy2(file_obj.file_path + '.backup', file_obj.file_path)
                os.remove(file_obj.file_path + '.backup')
            raise e
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating version: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/versions")
def get_file_versions(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get the file
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user has access to the file
        if file.owner_id != current_user.id:
            shared_file = db.query(models.FileShare).filter(
                models.FileShare.file_id == file_id,
                models.FileShare.shared_with_id == current_user.id
            ).first()
            if not shared_file:
                # Check if file is accessible via a shared folder
                if not is_file_accessible_by_shared_folder(db, file, current_user.id):
                    raise HTTPException(status_code=403, detail="Access denied")
        
        # Get all versions
        versions = db.query(models.FileVersion).filter(
            models.FileVersion.file_id == file_id
        ).order_by(models.FileVersion.version_number.asc()).all()
        
        return versions
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting versions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/versions/{version_number}/content")
async def get_version_content(
    file_id: int,
    version_number: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get the file
        file = db.query(models.File).filter(models.File.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user has access to the file
        if file.owner_id != current_user.id:
            shared_file = db.query(models.FileShare).filter(
                models.FileShare.file_id == file_id,
                models.FileShare.shared_with_id == current_user.id
            ).first()
            if not shared_file:
                # Check if file is accessible via a shared folder
                if not is_file_accessible_by_shared_folder(db, file, current_user.id):
                    raise HTTPException(status_code=403, detail="Access denied")
        
        # Get the version
        version = db.query(models.FileVersion).filter(
            models.FileVersion.file_id == file_id,
            models.FileVersion.version_number == version_number
        ).first()
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        if not os.path.exists(version.file_path):
            raise HTTPException(status_code=404, detail="Version file not found")
        
        # For text-based files, return the content
        if file.file_type.startswith('text/') or file.file_type in [
            'application/json', 'application/xml',
            'application/x-python', 'text/x-python',
            'text/x-java', 'text/x-c++', 'text/x-c',
            'text/x-php', 'text/x-ruby', 'text/x-swift',
            'application/javascript', 'text/javascript',
            'text/css', 'text/html'
        ]:
            try:
                with open(version.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content}
            except Exception as e:
                logger.error(f"Error reading version content: {str(e)}")
                raise HTTPException(status_code=500, detail="Error reading version content")
        else:
            # For binary files, return the file
            try:
                return FileResponse(
                    version.file_path,
                    media_type=file.file_type,
                    filename=f"v{version_number}_{file.filename}"
                )
            except Exception as e:
                logger.error(f"Error serving version file: {str(e)}")
                raise HTTPException(status_code=500, detail="Error serving version file")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting version content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/{file_id}/versions/{version_number}/restore")
async def restore_file_version(
    file_id: int,
    version_number: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Restore a file to a specific version."""
    # Get the version
    version = db.query(models.FileVersion).filter(
        models.FileVersion.file_id == file_id,
        models.FileVersion.version_number == version_number
    ).first()
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Get the file
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check if user has access to the file
    if file.owner_id != current_user.id:
        # Check if file is shared with user and has edit permission
        share = db.query(models.FileShare).filter(
            models.FileShare.file_id == file_id,
            models.FileShare.shared_with_id == current_user.id,
            models.FileShare.permission == 'edit'
        ).first()
        if not share:
            raise HTTPException(status_code=403, detail="Not authorized to restore versions")
    
    try:
        # Create a backup of current file
        backup_path = file.file_path + '.backup'
        shutil.copy2(file.file_path, backup_path)
        
        try:
            # Copy the version content to the current file
            shutil.copy2(version.file_path, file.file_path)
            
            # Update the current version in the database
            db.query(models.FileVersion).filter(
                models.FileVersion.file_id == file_id
            ).update({"is_current": False})
            
            version.is_current = True
            db.commit()
            
            return {
                "message": "Version restored successfully",
                "version": version
            }
        except Exception as e:
            # If anything goes wrong, restore from backup
            shutil.copy2(backup_path, file.file_path)
            raise e
        finally:
            # Clean up backup file
            if os.path.exists(backup_path):
                os.remove(backup_path)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_id}/versions/{version_number}")
def delete_file_version(
    file_id: int,
    version_number: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get the file
    file = db.query(models.File).filter(models.File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if user has permission to delete versions
    if file.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete versions of this file")

    # Get the version
    version = db.query(models.FileVersion).filter(
        models.FileVersion.file_id == file_id,
        models.FileVersion.version_number == version_number
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Get the latest version number for this file
    latest_version = db.query(models.FileVersion).filter(
        models.FileVersion.file_id == file_id
    ).order_by(models.FileVersion.version_number.desc()).first()
    if latest_version and version.version_number == latest_version.version_number:
        raise HTTPException(status_code=400, detail="Cannot delete the current version of a file")

    try:
        # Delete the version
        versioning.delete_version(db, file, version_number)
        return {"message": "Version deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting version: {str(e)}")

# Admin Endpoints
@app.get("/admin/users", response_model=List[schemas.User])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.get("/admin/users/{user_id}", response_model=schemas.User)
def get_user_by_id(
    user_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/admin/users/{user_id}", response_model=schemas.User)
def update_user_by_admin(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user

@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    try:
        # Get the user to delete
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user is authorized to delete
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Not authorized to delete this user")
        
        # Delete the user
        db.delete(user)
        db.commit()
        
        return {"message": "User deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def create_default_admin(db: Session):
    """Create default admin user if it doesn't exist"""
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        hashed_password = get_password_hash("admin")
        admin = models.User(
            email="admin@admin.com",
            username="admin",
            hashed_password=hashed_password,
            is_admin=True
        )
        db.add(admin)
        db.commit()
        logger.info("Default admin user created")
    return admin

@app.on_event("startup")
async def startup_event():
    """Create default admin on startup"""
    db = next(get_db())
    create_default_admin(db)

class AdminPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

@app.patch("/admin/change-password")
def change_admin_password(
    password_update: AdminPasswordUpdate,
    current_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Change admin password"""
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Only default admin can change password")
    
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Validate new password
    if len(password_update.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")
    
    # Update password
    current_user.hashed_password = get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "Admin password updated successfully"}

# 1. Alias for user registration
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return await register_user(user, db)

# 2. User management endpoints
@app.get("/users/{user_id}", response_model=schemas.User)
def get_user_by_id(user_id: int, current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Allow self or admin
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user_update: schemas.UserUpdate, current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Allow self or admin
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "email":
            existing_user = db.query(models.User).filter(models.User.email == value, models.User.id != user_id).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
        elif field == "username":
            existing_user = db.query(models.User).filter(models.User.username == value, models.User.id != user_id).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="Username already taken")
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Allow self or admin
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# 3. Admin: list all users
@app.get("/users/", response_model=List[schemas.User])
def list_users(current_user: models.User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

# 4. Alias for folder creation
@app.post("/files/folders", response_model=schemas.File)
def create_folder_alias(folder_data: schemas.FolderCreate, current_user: models.User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return create_folder(folder_data, current_user, db)

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