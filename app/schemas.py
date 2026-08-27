from pydantic import ConfigDict, BaseModel, EmailStr, field_validator, Field
from typing import Optional, Literal
from datetime import datetime
from .models import UserRole

class CompanyCreate(BaseModel):
    name: str

class CompanyOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamCreate(BaseModel):
    name: str
    manager_id: Optional[int] = None

class TeamOut(BaseModel):
    id: int
    name: str
    company_id: int
    manager_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    manager_id: Optional[int] = None

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
    password: str
    full_name: str
    role: UserRole = UserRole.sales

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be atleast 8 character long")
        return value

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
    team_id: Optional[int] = None
    is_active: bool
    is_verified: bool
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

class PipelineStageCreate(BaseModel):
    name: str
    order: int
    is_won: bool = False
    is_lost: bool = False

class PipelineStageOut(BaseModel):
    id: int
    company_id: int
    name: str
    order: int
    is_won: bool
    is_lost: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PipelineStageUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None
    is_won: Optional[bool] = None
    is_lost: Optional[bool] = None

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class TagOut(BaseModel):
    id: int
    company_id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9+\-\s]{7,15}$")
    company: Optional[str] = None
    stage_id: Optional[int] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^[0-9+\-\s]{7,15}$")
    company: Optional[str] = None
    stage_id: Optional[int] = None
    assigned_to: Optional[int] = None

class LeadOut(BaseModel):
    id: int 
    company_id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    stage_id: Optional[int] = None
    stage: Optional["PipelineStageOut"] = None
    owner_id: int
    assigned_to: Optional[int]
    author: UserOut
    tags: list[TagOut] = []
    deleted_at: Optional[datetime] = None
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
    stage_id: Optional[int] = None
    stage: Optional["PipelineStageOut"] = None
    owner_id: int
    tags: list[TagOut] = []
    assigned_to: Optional[int]
    deleted_at: Optional[datetime] = None
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
    parent_id: Optional[int] = None

class NoteOut(BaseModel):
    id: int
    content: str
    lead_id: int
    user_id: int
    parent_id: Optional[int]
    user: UserOut
    deleted_at: Optional[datetime] = None
    created_at: datetime
    replies: list["NoteOut"] = []

    model_config = ConfigDict(from_attributes=True)

NoteOut.model_rebuild()

class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    lead_id: Optional[int]
    is_read: bool
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
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[datetime] = None
    assigned_to: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    priority: Optional[Literal["low", "medium", "high"]] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[int] = None
    is_completed: Optional[bool] = None

class TaskOut(BaseModel):
    id: int
    title: str
    lead_id: int
    assigned_to: Optional[int]
    priority: str
    due_date: Optional[datetime]
    is_completed: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

class LeadByStageOut(BaseModel):
    stage_name: str
    count: int

class TasksSummaryOut(BaseModel):
    total: int
    completed: int
    overdue: int

class TeamPerformanceOut(BaseModel):
    team_name: str
    total_leads: int
    won_leads: int

class DashboardSummaryOut(BaseModel):
    total_leads: int
    open_leads: int
    won_leads: int
    lost_leads: int
    leads_by_stage: list[LeadByStageOut]
    tasks: TasksSummaryOut
    team_performance: list[TeamPerformanceOut]

class SearchLeadResult(BaseModel):
    id: int
    name: str
    email: Optional[str]
    company: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class SearchUserResult(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

class SearchTaskResult(BaseModel):
    id: int
    title: str
    lead_id: int
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)

class SearchCompanyResult(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class GlobalSearchOut(BaseModel):
    lead: list[SearchLeadResult]
    user: list[SearchUserResult]
    task: list[SearchTaskResult]
    company: list[SearchCompanyResult]

class AuditLogOut(BaseModel):
    id: int
    table_name: str
    record_id: int
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be atleast 8 characters long")
        return value

class SessionOut(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)