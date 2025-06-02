from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional
from datetime import datetime

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = user.password  # Password is already hashed in the schema
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_file(db: Session, file_id: int):
    return db.query(models.File).filter(models.File.id == file_id).first()

def get_user_files(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.File).filter(
        models.File.owner_id == user_id
    ).offset(skip).limit(limit).all()

def create_file(db: Session, file: schemas.FileCreate, user_id: int):
    db_file = models.File(
        **file.dict(),
        owner_id=user_id,
        upload_date=datetime.utcnow()
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def delete_file(db: Session, file_id: int):
    db_file = db.query(models.File).filter(models.File.id == file_id).first()
    if db_file:
        db.delete(db_file)
        db.commit()
    return db_file

def create_file_share(db: Session, file_id: int, share: schemas.FileShareCreate):
    db_share = models.FileShare(
        file_id=file_id,
        shared_with_id=share.shared_with_id,
        permission=share.permission,
        share_date=datetime.utcnow()
    )
    db.add(db_share)
    db.commit()
    db.refresh(db_share)
    return db_share

def get_shared_files(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.File).join(
        models.FileShare
    ).filter(
        models.FileShare.shared_with_id == user_id
    ).offset(skip).limit(limit).all()

def create_file_version(db: Session, file_id: int, version: schemas.FileVersionCreate, user_id: int):
    db_version = models.FileVersion(
        **version.dict(),
        file_id=file_id,
        created_by=user_id,
        created_at=datetime.utcnow()
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    return db_version

def get_file_versions(db: Session, file_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.FileVersion).filter(
        models.FileVersion.file_id == file_id
    ).offset(skip).limit(limit).all() 