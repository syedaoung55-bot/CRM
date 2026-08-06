from fastapi import APIRouter, Depends, status, Response, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..utils.file_handler import save_file, delete_file
from ..database import get_db
from typing import Optional, List
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, require_admin, create_activity_log)

router = APIRouter(
    prefix = f"/api/leads",
    tags = ["Notes"]
)

@router.post("/{id}/file", status_code=status.HTTP_201_CREATED, response_model=schemas.FileOut)
async def Upload_file(id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                      current_user: models.User = Depends(oauth2.get_current_user)):
    lead = get_lead_or_404(id, db, current_user)

    file_info = await save_file(file, id)

    new_file = models.LeadFile(
        **file_info,
        lead_id = id,
        user_id = current_user.id
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    create_activity_log(
        action = "New file uploaded.",
        description = f"File {file.filename} uploaded to lead {lead.name}.",
        lead_id = id,
        user_id = current_user.id, # type: ignore
        db = db
    )

    return new_file

@router.get("/{id}/file", response_model=List[schemas.FileOut])
def get_file(id: int, db: Session = Depends(get_db), 
             current_user: models.User = Depends(oauth2.get_current_user)):
    get_lead_or_404(id, db, current_user)

    files = db.query(models.LeadFile).filter(models.LeadFile.lead_id == id).all()
    
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No file has been uploaded for lead id {id}.")

    return files

@router.delete("/{id}/file/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_route(id: int, file_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    get_lead_or_404(id, db, current_user)

    file = db.query(models.LeadFile).filter(models.LeadFile.id == file_id, models.LeadFile.lead_id == id
                    ).first()

    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail = "File not found.")
    
    delete_file(file.filepath) # type: ignore

    db.delete(file)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)