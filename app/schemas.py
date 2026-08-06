from pydantic import ConfigDict, BaseModel, EmailStr, field_validator, Field
from typing import Optional, Literal
from datetime import datetime
from .models import UserRole, LeadStatus

class CompanyCreate(BaseModel):
    name: str

class CompanyOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be atleast 8 character long")
        return value

class UserInvite(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.sales

    @field_validator("role")
    @classmethod
    def validate_invitable_role(cls, value):
        if value == UserRole.admin:
            raise ValueError("Admins cannot be created via invite. Only manager or sales roles are allowed.")
        return value

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    company: CompanyOut
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    company_id: int
    company_name: str
    role: str

class TokenData(BaseModel):
    id: Optional[int] = None
    role: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LeadCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9+\-\s]{7,15}$")
    company: Optional[str] = None
    status: LeadStatus = LeadStatus.new

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9+\-\s]{7,15}$")
    company: Optional[str] = None
    status: Optional[LeadStatus] = LeadStatus.new
    assigned_to: Optional[int] = None

class LeadOut(BaseModel):
    id: int 
    company_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    status: str
    owner_id: int
    assigned_to: Optional[int]
    author: UserOut
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadOut1(BaseModel):
    id: int 
    company_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    status: str
    owner_id: int
    assigned_to: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadAssign(BaseModel):
    assigned_to: int = Field(gt = 0)

class NoteCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=1000
    )

class NoteOut(BaseModel):
    id: int
    content: str
    lead_id: int
    user_id: int
    user: UserOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ActivityLogOut(BaseModel):
    id: int
    action: str
    description: Optional[str]
    lead_id: Optional[int]
    user_id: int
    user: UserOut
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FileOut(BaseModel):
    id: int
    filename: str
    filepath: str
    filetype: str
    filesize: int
    lead_id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
