from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from ..utils.file_handler import delete_file
from ..database import get_db
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, check_lead_permission, check_lead_view_permission, 
                           create_activity_log, create_notification, require_admin, 
                           log_field_changes)

router = APIRouter(
    prefix="/api/v1/leads",
    tags = ['Tasks'])

@router.post("/{id}/tasks", status_code=status.HTTP_201_CREATED, response_model=schemas.TaskOut)
def create_task(id: int, task: schemas.TaskCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    assignee = None
    if task.assigned_to:
        assignee = db.query(models.User).filter(models.User.id == task.assigned_to,
                            models.User.company_id == current_user.company_id).first()
        if not assignee: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to assign not found.")

    new_task = models.Task(
        title = task.title,
        lead_id = id,
        assigned_to = task.assigned_to,
        priority = task.priority,
        due_date = task.due_date
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    create_activity_log(
        action = "Task Created",
        description = f"Task {new_task.title} is added to lead {lead.name}.",
        lead_id = id,
        user_id = current_user.id, # type: ignore
        db = db
    )

    if assignee and assignee.id != current_user.id:  # type: ignore
        create_notification(
            db = db,
            user_id = assignee.id,  # type: ignore
            type = models.NotificationType.task_assignment.value,
            message=f"You were assigned task '{new_task.title}' on lead '{lead.name}'.",
            lead_id = id  
        )

    return new_task


@router.get("/{id}/tasks", response_model=List[schemas.TaskOut])
def get_task(id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    return db.query(models.Task).filter(models.Task.lead_id == id, models.Task.deleted_at.is_(None))\
        .order_by(models.Task.due_date.asc()).all()

@router.get("/{id}/tasks/deleted", response_model=List[schemas.TaskOut])
def get_deleted_tasks(id: int, db: Session = Depends(get_db),
                      current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)

    return db.query(models.Task).filter(models.Task.lead_id == id, 
                            models.Task.deleted_at.isnot(None)).all()

@router.put("/{id}/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(id: int, task_id: int, update_task: schemas.TaskUpdate, db: Session = Depends(get_db),

                current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.lead_id == id, 
                                        models.Task.deleted_at.is_(None)).first()
    if not task: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with {task_id} not found.")

    updated_data = update_task.model_dump(exclude_unset=True)

    new_assignee = None
    reassigned = False
    if "assigned_to" in updated_data and updated_data["assigned_to"] is not None:
        new_assignee = db.query(models.User).filter(models.User.id == updated_data["assigned_to"],
            models.User.company_id == current_user.company_id
        ).first()
        if not new_assignee: 
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to assign not found.")
        reassigned = task.assigned_to != new_assignee.id

    before = {field: getattr(task, field) for field in updated_data }

    for field, value in updated_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    after = {field: getattr(task, field) for field in updated_data}

    log_field_changes(db, "tasks", task.id, before, after, current_user.id, current_user.company_id) #type: ignore

    if reassigned and new_assignee.id != current_user.id: # type: ignore
        create_notification(
            db=db,
            user_id=new_assignee.id, # type: ignore
            type=models.NotificationType.task_assignment.value,
            message=f"You were assigned task '{task.title}' on lead '{lead.name}'.",
            lead_id=id,
        )

    return task

@router.delete("/{id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, task_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.lead_id == id, 
                                        models.Task.deleted_at.is_(None)).first()
    if not task: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with {task_id} not found.")

    task.deleted_at = datetime.now(timezone.utc) # type: ignore
    task.deleted_by = current_user.id
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{id}/tasks/{task_id}/restore", response_model=schemas.TaskOut)
def restore_task(id: int, task_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.lead_id == id, 
        models.Task.deleted_at.isnot(None)).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"Deleted task with id {task_id} is not found.")

    task.deleted_at = None #type: ignore
    task.deleted_by = None #type: ignore
    db.commit()
    db.refresh(task)

    return task

@router.delete("/{id}/tasks/{task_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_task(id: int, task_id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    task = db.query(models.Task).filter(models.Task.id == task_id, models.Task.lead_id == id, 
        models.Task.deleted_at.isnot(None)).first()
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Task must be soft-deleted before it can be permanently deleted.")

    db.delete(task)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)