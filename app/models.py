from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime
from .database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    auth_uuid = Column(String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4()))

    files = relationship("File", back_populates="owner")
    shared_files = relationship("FileShare", back_populates="shared_with")
    created_versions = relationship("FileVersion", back_populates="created_by_user")

class FileType(str, enum.Enum):
    FILE = "file"
    FOLDER = "folder"

class PermissionType(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

class FileVersion(Base):
    __tablename__ = "file_versions"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"))
    version_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"))
    comment = Column(Text, nullable=True)
    is_current = Column(Boolean, default=False)

    # Relationships
    file = relationship("File", back_populates="versions")
    created_by_user = relationship("User", back_populates="created_versions", foreign_keys=[created_by])

    class Config:
        orm_mode = True

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String, nullable=True) # file_path is null for folders
    file_size = Column(Integer)  # Size in bytes
    file_type = Column(String, nullable=True) # file_type is null for folders
    upload_date = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_shared = Column(Boolean, default=False)
    type = Column(String, default='file') # 'file' or 'folder'
    parent_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    mime_type = Column(String, nullable=True)

    owner = relationship("User", back_populates="files")
    shares = relationship("FileShare", back_populates="file")
    # Relationship for children files/folders within this folder
    children = relationship("File", backref="parent", remote_side=[id])
    versions = relationship("FileVersion", back_populates="file", cascade="all, delete-orphan")

class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"))
    shared_with_id = Column(Integer, ForeignKey("users.id"))
    permission = Column(Enum(PermissionType), default=PermissionType.READ)
    share_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    file = relationship("File", back_populates="shares")
    shared_with = relationship("User", back_populates="shared_files") 