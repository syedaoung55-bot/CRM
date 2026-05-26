from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey, Enum, Text
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
import enum
from .database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    sales = "sales"

class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    won = "won"
    lost = "lost"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.sales)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, nullable=True)
    status = Column(Enum(LeadStatus), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=text('now()'),
                       server_default=text('now()') )
    
    files = relationship("LeadFile", back_populates="lead", cascade="all, delete")
    author = relationship("User", foreign_keys=[owner_id])
    assign = relationship("User", foreign_keys=[assigned_to])
    
class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    
    user = relationship("User", foreign_keys=[user_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    lead = relationship("Lead", back_populates="files")
    user = relationship("User")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, nullable=False)
    token = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), 
                        nullable=False, server_default=text('now()'))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    user = relationship("User")