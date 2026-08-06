from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, oauth2
from ..permissions import (check_note_permission, create_activity_log, get_lead_or_404)

router = APIRouter(
    prefix = f"/api/v1/leads",
    tags = ["Notes"]
)

@router.post("/{id}/notes", status_code=status.HTTP_201_CREATED, response_model=schemas.NoteOut)
def create_note(id: int, note: schemas.NoteCreate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)
    new_note = models.Note(
        content = note.content,
        lead_id = id,
        user_id = current_user.id
    )

    db.add(new_note)
    db.commit()
    db.refresh(new_note)

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
         ).order_by(models.Note.created_at.desc()).all()

    check_note_permission(notes, current_user)
    
    return notes

@router.delete("/{id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(id: int, note_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    
    lead = get_lead_or_404(id, db, current_user)
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.lead_id == id
            ).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Note with id {id} is not found.")

    check_note_permission(note, current_user)

    db.delete(note)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)