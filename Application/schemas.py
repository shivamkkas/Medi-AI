from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    """
    Enum representing user roles
    Using string values for easy serialization and comparison
    """
    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"
    SUPERADMIN = "super"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool

class UserProfileCreate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    bio: Optional[str] = None
    health_conditions: Optional[str] = None

class SYMPTOM(BaseModel):
    symptom: str
    
class DIET(BaseModel):
    dietary_preferences:str
    fitness_goals:str
    lifestyle_factors:str
    dietary_restrictions:str
    health_conditions:str
    user_query:str


from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

# Existing imports and enums remain the same as in the original file

# Token Schemas for Authentication
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr]
    user_id:Optional[str]
    # role: Optional[UserRole] = None
    # exp: Optional[datetime] = None

# Login Schema with Enhanced Validation
class UserLogin(BaseModel):
    username: str
    password: str

    # @validator('password')
    # def validate_password(cls, v):
    #     """
    #     Password strength validation
    #     - At least 8 characters
    #     - Must contain uppercase and lowercase letters
    #     - Must contain at least one number
    #     """
    #     if len(v) < 8:
    #         raise ValueError('Password must be at least 8 characters long')
        
    #     if not any(c.isupper() for c in v):
    #         raise ValueError('Password must contain at least one uppercase letter')
        
    #     if not any(c.islower() for c in v):
    #         raise ValueError('Password must contain at least one lowercase letter')
        
    #     if not any(c.isdigit() for c in v):
    #         raise ValueError('Password must contain at least one number')
        
    #     return v

# Password Reset Schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        """
        Enhanced password reset validation
        """
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        
        if not any(c.isupper() for c in v):
            raise ValueError('New password must contain at least one uppercase letter')
        
        if not any(c.islower() for c in v):
            raise ValueError('New password must contain at least one lowercase letter')
        
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain at least one number')
        
        return v

# Two-Factor Authentication Schemas
class TwoFactorSetup(BaseModel):
    method: str = Field(..., description="Two-factor authentication method")
    contact_info: str = Field(..., description="Phone number or email for 2FA")

class TwoFactorVerification(BaseModel):
    verification_code: str = Field(..., min_length=6, max_length=6)

# User Preferences and Security Settings
class UserSecuritySettings(BaseModel):
    two_factor_enabled: bool = False
    login_notifications: bool = False
    privacy_mode: bool = False

# Audit Log Entry Schema
class AuditLogEntry(BaseModel):
    user_id: int
    action: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

# Enhanced User Response with Additional Fields
class EnhancedUserResponse(UserResponse):
    last_login: Optional[datetime] = None
    security_settings: Optional[UserSecuritySettings] = None
    
    class Config:
        orm_mode = True

# Social Authentication Schema
class SocialAuthRequest(BaseModel):
    provider: str = Field(..., description="Social authentication provider")
    access_token: str = Field(..., description="Access token from social provider")

