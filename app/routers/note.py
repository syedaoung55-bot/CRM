from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from datetime import datetime, timezone
from ..utils.file_handler import delete_file
from typing import Optional, List
from .. import schemas, models, oauth2
from ..permissions import (check_note_permission, create_activity_log, get_lead_or_404, 
                           extract_mentions, create_notification, require_admin)

router = APIRouter(
    prefix = f"/api/v1/leads",
    tags = ["Notes"]
)

@router.post("/{id}/notes", status_code=status.HTTP_201_CREATED, response_model=schemas.NoteOut)
def create_note(id: int, note: schemas.NoteCreate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)

    if note.parent_id:
        parent = db.query(models.Note).filter(models.Note.id == note.parent_id,
                            models.Note.lead_id == id, models.Note.deleted_at.is_(None)).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent note not found on this lead.")

    new_note = models.Note(
        content = note.content,
        lead_id = id,
        user_id = current_user.id,
        parent_id = note.parent_id
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    mentioned_ids = extract_mentions(note.content, db, current_user.company_id) # type: ignore
    for user_id in mentioned_ids:
        db.add(models.Note_Mention(note_id=new_note.id, mentioned_user_id=user_id))
        if user_id != current_user.id: #type: ignore
            create_notification(
                db = db,
                user_id = user_id, #type: ignore
                type = models.NotificationType.mention.value,
                message=f"{current_user.full_name} mentioned you in a note on lead '{lead.name}'.", 
                lead_id=id
            )
    if mentioned_ids:
        db.commit()

    create_activity_log(
        action = "New Note Created.",
        description = f"Note is added to {lead.name} from user {current_user.full_name}.",
        lead_id = id,
        user_id = current_user.id, # type: ignore
        db = db
    )

    return new_note

@router.get("/{id}/notes", response_model = list[schemas.NoteOut])
def get_notes(id: int, db: Session = Depends(get_db), current_user: models.User = 
              Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)    

    notes = db.query(models.Note).filter(models.Note.lead_id == id, 
    models.Note.parent_id.is_(None), models.Note.deleted_at.is_(None)
    ).order_by(models.Note.created_at.desc()).all()
    
    return notes

@router.get("/{id}/notes/deleted", response_model=List[schemas.NoteOut])
def get_deleted_notes(id: int, db: Session = Depends(get_db),
                      current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)

    return db.query(models.Note).filter(models.Note.lead_id == id, 
                            models.Note.deleted_at.isnot(None)).all()

@router.delete("/{id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(id: int, note_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    
    lead = get_lead_or_404(id, db, current_user)
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.lead_id == id, 
            models.Note.deleted_at.is_(None)).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Note with id {id} is not found.")

    check_note_permission(note, current_user)

    note.deleted_at = datetime.now(timezone.utc) # type: ignore
    note.deleted_by = current_user.id
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{id}/notes/{note_id}/restore", response_model=schemas.NoteOut)
def restore_note(id: int, note_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    note = db.query(models.Note).filter(models.Note.id == note_id, 
                        models.Note.lead_id == id, models.Note.deleted_at.isnot(None)).first()
    
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deleted note with id {note_id} is not found.")

    note.deleted_at = None # type: ignore
    note.deleted_by = None # type: ignore
    db.commit()
    db.refresh(note)

    return note


@router.delete("/{id}/notes/{note_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_note(id: int, note_id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.lead_id == id, 
                        models.Note.deleted_at.isnot(None)).first()
    
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Note must be soft-deleted before it can be permanently deleted.")

    db.delete(note)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)