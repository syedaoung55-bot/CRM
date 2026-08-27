from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Enum, Text
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
import enum
from .database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    sales = "sales"

class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class NotificationType(str, enum.Enum):
    assignment = "assignment"
    mention = "mention"
    task_assignment = "task_assignment"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.sales)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)

    
    team = relationship("Team", back_populates="members", foreign_keys=[team_id])
    company = relationship('Company', back_populates='users')

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    stage_id = Column(Integer, ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=text('now()'),
                       server_default=text('now()') )
    
    files = relationship("LeadFile", back_populates="lead", cascade="all, delete")
    author = relationship("User", foreign_keys=[owner_id])
    assign = relationship("User", foreign_keys=[assigned_to])
    stage = relationship("PipelineStage")
    tenant = relationship('Company', back_populates='leads')
    tags = relationship("Tag", secondary="lead_tags", back_populates="leads")
    deleter = relationship("User", foreign_keys=[deleted_by])

class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
    is_won = Column(Boolean, nullable=False, default=False)
    is_lost = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

    company = relationship("Company")

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=True, index=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    
    user = relationship("User", foreign_keys=[user_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    replies = relationship("Note", back_populates="parent", cascade="all, delete")
    parent = relationship("Note", back_populates="replies", remote_side=[id])
    deleter = relationship("User", foreign_keys=[deleted_by])

class Note_Mention(Base):
    __tablename__ = "note_mentions"

    id = Column(Integer, primary_key=True, nullable=False)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                            nullable=False, server_default=text('now()'))

    note = relationship("Note")
    mentioned_user = relationship("User")
    
class Activity_Log(Base):
    __tablename__ = "activity_log"
    
    id = Column(Integer, primary_key=True, nullable=False)
    action= Column(String, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    
    user = relationship("User", foreign_keys=[user_id])
    lead = relationship("Lead", foreign_keys=[lead_id])

class LeadFile(Base):
    __tablename__ = "lead_files"

    id = Column(Integer, primary_key=True, nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    filetype = Column(String, nullable=False)
    filesize = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    lead = relationship("Lead", back_populates="files")
    user = relationship("User", foreign_keys=[user_id])
    deleter = relationship("User", foreign_keys=[deleted_by])

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, nullable=False)
    token = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    user = relationship("User")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                            nullable=False, server_default=text('now()'))

    users = relationship('User', back_populates='company')
    leads = relationship('Lead', back_populates='tenant')
    #tasks = relationship('Task', back_populates='company')

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                                nullable=False, server_default=text('now()'))
    company = relationship("Company")
    manager = relationship("User", foreign_keys=[manager_id])
    members = relationship("User", back_populates="team", foreign_keys="User.team_id")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, nullable=False)
    title = Column(String, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.medium)
    due_date = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    is_completed = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                                    nullable=False, server_default=text('now()'))

    lead = relationship("Lead")
    assignee = relationship("User", foreign_keys=[assigned_to])
    deleter = relationship("User", foreign_keys=[deleted_by])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False)
    message = Column(String, nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                                        nullable=False, server_default=text('now()'))

    user = relationship("User")
    lead = relationship("Lead")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                                        nullable=False, server_default=text('now()'))

    company = relationship("Company")
    leads = relationship("Lead", secondary="lead_tags", back_populates="tags")

class LeadTag(Base):
    __tablename__ = "lead_tags"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                                        nullable=False, server_default=text('now()'))

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                                        nullable=False, server_default=text('now()'))

    company = relationship("Company")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

class PasswordResetToken(Base):
    __tablename__ = "password_reset_token"

    id = Column(Integer, primary_key=True, nullable=False)
    token = Column(String, nullable=False, unique = True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                                            nullable=False, server_default=text('now()'))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

    user = relationship("User")

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_token"

    id = Column(Integer, primary_key=True, nullable=False)
    token = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                                                nullable=False, server_default=text('now()'))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)

    user = relationship("User")