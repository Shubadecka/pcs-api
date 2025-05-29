from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str
    device_identifier: str

class LoginResponse(BaseModel):
    is_valid: bool
    is_admin: Optional[bool] = None
    is_device_remembered: Optional[bool] = None
    message: str

class TwoFactorAuthRequest(BaseModel):
    username: str
    validation_code: str

class TwoFactorAuthResponse(BaseModel):
    is_valid: bool
    message: str
