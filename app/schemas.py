from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from pydantic import validator
from .models import PermissionType

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class FileBase(BaseModel):
    name: str
    size: int
    mime_type: Optional[str] = None
    is_folder: bool = False
    parent_id: Optional[int] = None

class FileCreate(FileBase):
    pass

class File(FileBase):
    id: int
    s3_key: str
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool = False
    version: int = 1

    class Config:
        from_attributes = True

class FileShareBase(BaseModel):
    file_id: int
    shared_with_id: int
    permission: PermissionType = PermissionType.READ

class FileShareCreate(BaseModel):
    shared_with_email: str
    permission: str = 'read'
    # For backward compatibility
    shared_with_id: Optional[int] = None

class FileShare(FileShareBase):
    id: int
    share_date: datetime

    class Config:
        from_attributes = True

class MoveItem(BaseModel):
    target_parent_id: Optional[int] = None

class FileVersionBase(BaseModel):
    version_number: int
    file_size: int
    comment: Optional[str] = None
    is_current: bool = False

class FileVersionCreate(FileVersionBase):
    pass

class FileVersion(BaseModel):
    id: int
    file_id: int
    file_path: str
    created_at: datetime
    created_by: int
    version_number: int
    file_size: int
    comment: Optional[str] = None
    is_current: bool = False

    class Config:
        from_attributes = True

class FileVersionWithUser(FileVersion):
    created_by: User

    class Config:
        from_attributes = True

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

class FileMove(BaseModel):
    target_parent_id: Optional[int] = None 