from fastapi import HTTPException, Depends, status
from .models import UserRole
from typing import Optional
from sqlalchemy.orm import Session
from app import models, oauth2
from .database import get_db

def get_lead_or_404(id: int, db: Session):
    lead = db.query(models.Lead).filter(models.Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lead with id {id} is not found.")
    return lead

def check_lead_permission(lead, current_user):
    if current_user.role == UserRole.admin:
        return True
    
    if current_user.role == UserRole.manager:
        if lead.assigned_to != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only modify the leads Assigned to you.")
        
    if current_user.role == UserRole.sales:
        if lead.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only modify your own leads.")

    if current_user.role == UserRole.manager:
            if lead.owner_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can only modify your own leads or leads assigned to you.")
        
def check_lead_view_permission(lead, current_user):
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