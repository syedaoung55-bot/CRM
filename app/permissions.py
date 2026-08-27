from fastapi import HTTPException, Depends, status
from .models import UserRole
import re
from typing import Optional
from sqlalchemy.orm import Session
from app import models, oauth2
from .database import get_db

def scoped(query, model, current_user):
    query = query.filter(model.company_id == current_user.company_id)
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    return query

def get_lead_or_404(id: int, db: Session, current_user):
    lead = scoped(db.query(models.Lead), models.Lead, current_user).filter(models.Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lead with id {id} is not found.")
    return lead

def check_lead_permission(lead, current_user, db):
    if lead.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lead with id {lead.id} is not found.")
    
    if current_user.role == UserRole.admin:
        return True
    
    if current_user.role == UserRole.manager:
        managed_team = db.query(models.Team).filter(models.Team.manager_id == current_user.id).first()

        assignee = db.query(models.User).filter(models.User.id == lead.assigned_to).first()

        if not managed_team or not assignee or assignee.team_id != managed_team.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only modify the leads Assigned to your Team.")
        return True

        
    if current_user.role == UserRole.sales:
        if lead.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only modify your own leads.")

def check_team_permission(team, current_user):
    if team.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Team with id {team.id} is not found.")

    if current_user.role == UserRole.admin:
        return True

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Only admins can manage Teams.")
        
def check_lead_view_permission(lead, current_user):
    if lead.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lead with id {lead.id} is not found.")
    
    if current_user.role == UserRole.sales:
        if lead.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only view your own leads.")
        
def require_admin(current_user: models.User = Depends(oauth2.get_current_user)):
    if current_user.role.value != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins can perform this action.")
    
    return current_user
    
def require_admin_or_manager(current_user: models.User = Depends(oauth2.get_current_user)):
    if current_user.role not in [UserRole.admin, UserRole.manager]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins and managers can perform this action.")
    
    return current_user
    
def check_note_permission(note, current_user):
    if note.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only modify your own notes.")
        

def create_activity_log(action: str, db: Session, user_id: int,
                        description: Optional[str] = None,
                        lead_id: Optional[int] = None):
    log = models.Activity_Log(
        action=action,
        description=description,
        user_id=user_id,
        lead_id=lead_id
    )
    db.add(log)
    db.commit()

def extract_mentions(content: str, db: Session, company_id: int):

    if "@" not in content:
        return []

    users = db.query(models.User).filter(models.User.company_id == company_id).all()

    mentioned_ids = []
    for user in users:
        if f"@{user.full_name}" in content:
            mentioned_ids.append(user.id)

    return mentioned_ids

def create_notification(db: Session, user_id: int, type: str, message: str, lead_id: Optional[int] = None):
    notification = models.Notification(
        user_id = user_id,
        type = type,
        message = message,
        lead_id = lead_id
    )

    db.add(notification)
    db.commit()

def log_field_changes(db: Session, table_name: str, record_id: int, 
                      before: dict, after: dict, changed_by: int, company_id: int):
    
    for field, new_value in after.items():
        old_value = before.get(field)
        if old_value != new_value:
            db.add(models.AuditLog(
                company_id = company_id,
                table_name = table_name,
                record_id = record_id,
                field_name = field,
                old_value = str(old_value)
                if old_value is not None else None,
                new_value = str(new_value)
                if new_value is not None else None,
                changed_by = changed_by
            ))

    db.commit()

def require_verified_email(current_user: models.User = Depends(oauth2.get_current_user)):
    if not current_user.is_verified:  # type: ignore
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Please verify your email address before performing this action.")
    return current_user