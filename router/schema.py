from pydantic import BaseModel
from typing import Optional, List, Dict
from fastapi import UploadFile

class LoginRequest(BaseModel):
    username: str
    password: str
    device_identifier: str

class LoginResponse(BaseModel):
    is_correct_password: bool
    is_admin: Optional[bool] = None
    is_device_remembered: Optional[bool] = None
    message: str

class TwoFactorAuthRequest(BaseModel):
    username: str
    validation_code: str

class TwoFactorAuthResponse(BaseModel):
    is_valid: bool
    message: str

# Schemas for File Browser
class ListFilesRequest(BaseModel):
    path: str

class FileItem(BaseModel):
    name: str
    is_directory: bool
    # path: str # Optionally include full path

class ListFilesResponse(BaseModel):
    files: List[FileItem]
    # directories: List[str] # README implies separate lists, combining for simplicity in FileItem
    can_share_here: bool 
    message: Optional[str] = None

class UploadFileResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    transcription: Optional[str] = None

class CreateDirectoryRequest(BaseModel):
    path: str # Path to the new directory (e.g., "existing_folder/new_folder_name")
    current_user: str
    shared_with: Optional[List[str]] = [] # Usernames or IDs to share with

class CreateDirectoryResponse(BaseModel):
    success: bool
    message: str
    # directory_path: Optional[str] = None

class DownloadFileResponse(BaseModel):
    success: bool
    message: str
    file: Optional[bytes] = None

class DownloadDirectoryResponse(BaseModel):
    success: bool
    message: str
    file: Optional[bytes] = None

class DeleteFileResponse(BaseModel):
    success: bool
    message: str

class DeleteDirectoryResponse(BaseModel):
    success: bool
    message: str

class LLMConversation(BaseModel):
    role: str
    content: str

class LLMResponseRequest(BaseModel):
    user_id: int
    conversation: List[LLMConversation]
    model: str

class LLMResponseResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None

class GetUserRequest(BaseModel):
    action_user: str  # username of user performing action
    target_user: str  # username to get info for

class GetUserResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None
    directories: Optional[List[str]] = None
    is_admin: Optional[bool] = None
    is_disabled: Optional[bool] = None

class PostUserRequest(BaseModel):
    action_user: str  # username of user performing action
    username: str
    password: Optional[str] = None
    email: Optional[str] = None
    extra_directories: Optional[List[str]] = []
    remove_directories: Optional[List[str]] = []
    is_admin: Optional[bool] = None

class PostUserResponse(BaseModel):
    success: bool
    message: str
    directories: Optional[List[str]] = None
    is_admin: Optional[bool] = None

class DeleteUserRequest(BaseModel):
    action_user: str  # username of user performing action
    target_user: str  # username to disable

class DeleteUserResponse(BaseModel):
    success: bool
    message: str
