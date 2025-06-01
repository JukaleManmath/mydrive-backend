from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from pydantic import validator

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class FileBase(BaseModel):
    filename: str

class FileCreate(FileBase):
    pass

class FolderCreate(FileBase):
    parent_id: Optional[int] = None

class File(FileBase):
    id: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None  # Size in bytes
    file_type: Optional[str] = None
    upload_date: datetime
    owner_id: int
    is_shared: bool
    type: str
    parent_id: Optional[int] = None

    # To represent nested files/folders
    children: List['File'] = []

    class Config:
        from_attributes = True

# Update the forward reference for the File schema
File.model_rebuild()

class SharedFile(BaseModel):
    id: int
    filename: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_date: Optional[datetime] = None
    owner_id: int
    is_shared: bool
    type: str
    parent_id: Optional[int] = None
    permission: str
    children: List['File'] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        validate_assignment = True

    @validator('upload_date', pre=True)
    def parse_upload_date(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return value

    @validator('permission')
    def validate_permission(cls, v):
        if v not in ['read', 'edit']:
            raise ValueError('Permission must be either "read" or "edit"')
        return v

class FileShareCreate(BaseModel):
    shared_with_email: str
    permission: str = "read"

class FileShare(FileShareCreate):
    id: int
    share_date: datetime

    class Config:
        from_attributes = True

class MoveItem(BaseModel):
    target_parent_id: Optional[int] = None

class SharedFileResponse(BaseModel):
    id: int
    filename: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_date: Optional[str] = None  # Store as ISO format string
    owner_id: int
    is_shared: bool = False
    type: str = 'file'
    parent_id: Optional[int] = None
    permission: str = 'read'
    children: List['SharedFileResponse'] = []  # Changed from List['File'] to List['SharedFileResponse']

    class Config:
        from_attributes = True
        extra = 'allow'  # Allow extra fields

    @validator('permission')
    def validate_permission(cls, v):
        if v not in ['read', 'edit']:
            return 'read'  # Default to read if invalid
        return v

    @validator('type')
    def validate_type(cls, v):
        if v not in ['file', 'folder']:
            return 'file'  # Default to file if invalid
        return v

    @validator('is_shared', pre=True)
    def validate_is_shared(cls, v):
        if v is None:
            return False
        return bool(v)

# Update the forward reference for the SharedFileResponse schema
SharedFileResponse.model_rebuild()

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
        orm_mode = True

class FileVersionWithUser(FileVersion):
    created_by: User

    class Config:
        orm_mode = True 