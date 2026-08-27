from fastapi import APIRouter, Depends, status, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..utils.file_handler import delete_file
from ..utils.email import send_lead_assigned_email
from ..database import get_db
from typing import Optional, List
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, check_lead_permission, check_lead_view_permission,
                           require_admin, require_admin_or_manager, create_activity_log, scoped,
                           create_notification, log_field_changes)


router = APIRouter(
    prefix="/api/v1/leads",
    tags = ['Leads'])

@router.get("/", response_model=List[schemas.LeadOut1])
def get_all_leads(db: Session=Depends(get_db), current_user: models.User=Depends(oauth2.get_current_user),
                  limit: int=10, skip: int=0, search: Optional[str]="" , sort: Optional[str] = "created_at"):

    query = scoped(db.query(models.Lead), models.Lead, current_user)
    query1 = query.filter(models.Lead.name.contains(search))

    if current_user.role.value == models.UserRole.sales:
        query1 = query.filter(models.Lead.owner_id == current_user.id)

    return query1.order_by(models.Lead.created_at.desc()).limit(limit).offset(skip).all()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.LeadOut)
def create_lead(lead: schemas.LeadCreate, db: Session=Depends(get_db), 
                current_user: models.User =Depends(oauth2.get_current_user)):
    stage_id = lead.stage_id
    if stage_id is None:
        first_stage = db.query(models.PipelineStage).filter(
            models.PipelineStage.company_id == current_user.company_id
        ).order_by(models.PipelineStage.order.asc()).first()
        stage_id = first_stage.id if first_stage else None
    else:
        stage = db.query(models.PipelineStage).filter(
            models.PipelineStage.id == stage_id,
            models.PipelineStage.company_id == current_user.company_id
        ).first()
        if not stage:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid stage_id for your company.")
    
    lead = models.Lead(**lead.model_dump(exclude={"stage_id"}), 
                       owner_id = current_user.id, 
                       company_id = current_user.company_id, 
                       stage_id = stage_id)  
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

@router.get("/deleted", response_model=List[schemas.LeadOut])
def get_deleted_leads(db: Session = Depends(get_db), 
                      current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)

    return db.query(models.Lead).filter(models.Lead.company_id == current_user.company_id,
        models.Lead.deleted_at.isnot(None)).all()

@router.get("/{id}", response_model=schemas.LeadOut)
def get_lead(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    lead = get_lead_or_404(id, db, current_user)
    check_lead_view_permission(lead, current_user)

    return lead

@router.put("/{id}", response_model=schemas.LeadOut)
def update_lead(id: int, lead: schemas.LeadUpdate, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    updated_lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(updated_lead, current_user, db)
    old_stage_id = updated_lead.stage_id


    update_data = lead.model_dump(exclude_unset=True)

    before = {field: getattr(updated_lead, field) for field in update_data}

    for field, value in update_data.items():
        setattr(updated_lead, field, value)

    db.commit()
    db.refresh(updated_lead)

    after = {field: getattr(updated_lead, field) for field in update_data}

    log_field_changes(
        db = db,
        table_name = "leads",
        record_id = updated_lead.id, # type: ignore
        before = before,
        after = after,
        changed_by = current_user.id, # type: ignore
        company_id = current_user.company_id # type: ignore
    )

    if old_stage_id != updated_lead.stage_id: # type: ignore
        action = "Lead Updated and Stage changed"
        description = f"Status is changed from {old_stage_id} to {updated_lead.stage_id} and Lead {lead.name} is created by {current_user.email}"
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
                current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    lead_name = lead.name

    require_admin(current_user)

    lead.deleted_at = datetime.now(timezone.utc) # type: ignore
    lead.deleted_by = current_user.id
    db.commit()

    create_activity_log(
        action = "Lead Deleted",
        description = f"Lead {lead_name} is deleted by {current_user.email}", 
        user_id = current_user.id, # type: ignore
        lead_id = None,  
        db = db
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{id}/restore", response_model=schemas.LeadOut)
def restore_lead(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    lead = db.query(models.Lead).filter(models.Lead.id == id,models.Lead.company_id == current_user.company_id,
        models.Lead.deleted_at.isnot(None)).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Deleted lead with id {id} is not found.")

    lead.deleted_at = None # type: ignore
    lead.deleted_by = None # type: ignore
    db.commit()
    db.refresh(lead)

    create_activity_log(
        action="Lead Restored", 
        description=f"Lead {lead.name} was restored by {current_user.email}",
        user_id=current_user.id, # type: ignore
        lead_id=lead.id, # type: ignore
        db=db) 
    
    return lead

@router.delete("/{id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_lead(id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)
    lead = db.query(models.Lead).filter(models.Lead.id == id,models.Lead.company_id == current_user.company_id,
        models.Lead.deleted_at.isnot(None)).first()
    
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Deleted lead with id {id} is not found. A lead must be soft-deleted before it can be permanently deleted.")

    for file in db.query(models.LeadFile).filter(models.LeadFile.lead_id == id).all():
        delete_file(file.filepath) # type: ignore

    db.delete(lead)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch("/{id}/assign", response_model=schemas.LeadOut)
async def assign_lead(id: int, lead_assign: schemas.LeadAssign, background_tasks: BackgroundTasks, 
            db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    require_admin_or_manager(current_user)

    assigned_user = db.query(models.User).filter(models.User.id == lead_assign.assigned_to, 
                            models.User.company_id == current_user.company_id).first()

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

    create_notification(
        db = db,
        user_id = assigned_user.id,  # type: ignore
        type = models.NotificationType.assignment.value,
        message=f"You were assigned lead '{lead.name}' by {current_user.full_name}.",
        lead_id = lead.id  # type: ignore
    )

    background_tasks.add_task(
        send_lead_assigned_email,
        assigned_to_email=str(assigned_user.email),
        assigned_to_name=str(assigned_user.full_name),
        lead_name=str(lead.name),
        assigned_by_name=str(current_user.full_name),
    )
    return lead