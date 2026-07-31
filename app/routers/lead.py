from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from ..utils.email import send_lead_assigned_email
from ..database import get_db
from typing import Optional, List
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, check_lead_permission, check_lead_view_permission,
                           require_admin, require_admin_or_manager, create_activity_log)


router = APIRouter(
    prefix="/leads",
    tags = ['Leads'])

@router.get("/", response_model=List[schemas.LeadOut1])
def get_all_leads(db: Session=Depends(get_db), current_user: models.User=Depends(oauth2.get_current_user),
                  limit: int=10, skip: int=0, search: Optional[str]="" , sort: Optional[str] = "created_at"):

    lead = db.query(models.Lead).filter(models.Lead.name.contains(search)).order_by(models.Lead.created_at.desc()).limit(limit).offset(skip).all()

    if current_user.role.value == schemas.UserRole.sales.value:
        lead = db.query(models.Lead).filter(models.Lead.owner_id == current_user.id)

    return lead


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.LeadOut)
def create_lead(lead: schemas.LeadCreate, db: Session=Depends(get_db), 
                current_user: models.User =Depends(oauth2.get_current_user)):
    lead = models.Lead(**lead.model_dump(), owner_id = current_user.id)  
    db.add(lead)
    db.commit()
    db.refresh(lead)

    create_activity_log(
        action = "Lead Created",
        description = f"Lead {lead.name} is created by {current_user.email}", 
        user_id = current_user.id, # type: ignore
        lead_id = lead.id,  # pyright: ignore[reportArgumentType]
        db = db
    )

    return lead


@router.get("/{id}", response_model=schemas.LeadOut)
def get_Lead(id: int, db: Session = Depends(get_db), 
             current_user: models.User = Depends(oauth2.get_current_user)):

    lead = get_lead_or_404(id, db)
    check_lead_view_permission(lead, current_user)

    return lead

@router.put("/{id}", response_model=schemas.LeadOut)
def update_lead(id: int, lead: schemas.LeadUpdate, db: Session = Depends(get_db),
                current_user: models.User = Depends(check_lead_permission)):
    updated_lead = get_lead_or_404(id, db)
    old_status = updated_lead.status

    check_lead_permission(lead, current_user)

    update_data = lead.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(updated_lead, field, value)

    db.commit()
    db.refresh(updated_lead)

    if old_status.value != updated_lead.status.value:
        action = "Lead Updated and Status changed"
        description = f"Status is changed from {old_status} to {updated_lead.status} and Lead {lead.name} is created by {current_user.email}"
    else:
        action = "Lead Updated"
        description = f"Lead {lead.name} is created by {current_user.email}"

    create_activity_log(
        action = action,
        description = description,
        user_id = current_user.id, # type: ignore
        lead_id = updated_lead.id, # type: ignore
        db = db
    )
    return updated_lead

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_admin)):
    lead = get_lead_or_404(id, db)
    lead_name = lead.name

    db.delete(lead)
    db.commit()

    create_activity_log(
        action = "Lead Deleted",
        description = f"Lead {lead_name} is deleted by {current_user.email}", 
        user_id = current_user.id, # type: ignore
        lead_id = None,  
        db = db
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch("/{id}/assign", response_model=schemas.LeadOut)
async def assign_lead(id: int, lead_assign: schemas.LeadAssign, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_admin_or_manager)):
    lead = get_lead_or_404(id, db)

    assigned_user = db.query(models.User).filter(models.User.id == lead_assign.assigned_to).first()

    if not assigned_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User to assign not found.")
    
    if assigned_user.role.value != models.UserRole.sales:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="You can only assign Leads to the sales User.")
    
    lead.assigned_to = lead_assign.assigned_to # type: ignore
    db.commit()
    db.refresh(lead)

    create_activity_log(
        action = "Lead Assigned",
        description = f"Lead is Assigned to {assigned_user.full_name}",
        user_id = current_user.id, # type: ignore
        lead_id = lead.id, # type: ignore
        db = db
    )
    await send_lead_assigned_email(
        assigned_to_email = str(assigned_user.email),
        assigned_to_name = str(assigned_user.full_name),
        lead_name = str(lead.name),
        assigned_by_name = str(current_user.full_name)
     )
    return lead