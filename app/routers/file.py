from fastapi import APIRouter, Depends, status, Response, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..utils.file_handler import save_file, delete_file
from ..database import get_db
from datetime import datetime, timezone
from typing import List
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, require_admin, create_activity_log)

router = APIRouter(
    prefix = f"/api/v1/leads",
    tags = ["Files"]
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

    files = db.query(models.LeadFile).filter(models.LeadFile.lead_id == id, 
                    models.LeadFile.deleted_at.is_(None)).all()
    
    if not files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail = f"No file has been uploaded for lead id {id}.")

    return files

@router.get("/{id}/file/deleted", response_model=List[schemas.FileOut])
def get_deleted_files(id: int, db: Session = Depends(get_db),
                      current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)

    return db.query(models.LeadFile).filter(models.LeadFile.lead_id == id, 
                    models.LeadFile.deleted_at.isnot(None)).all()

@router.delete("/{id}/file/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_route(id: int, file_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(oauth2.get_current_user)):
    get_lead_or_404(id, db, current_user)

    file = db.query(models.LeadFile).filter(models.LeadFile.id == file_id, models.LeadFile.lead_id == id, 
                    models.LeadFile.deleted_at.is_(None)).first()

    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail = "File not found.")
    
    file.deleted_at = datetime.now(timezone.utc) # type: ignore
    file.deleted_by = current_user.id
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{id}/file/{file_id}/restore", response_model=schemas.FileOut)
def restore_file(id: int, file_id: int, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    file = db.query(models.LeadFile).filter(models.LeadFile.id == file_id, models.LeadFile.lead_id == id, 
        models.LeadFile.deleted_at.isnot(None)).first()
    
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deleted file with id {file_id} is not found.")

    file.deleted_at = None #type: ignore
    file.deleted_by = None #type: ignore
    db.commit()
    db.refresh(file)

    return file


@router.delete("/{id}/file/{file_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_file(id: int, file_id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(oauth2.get_current_user)):

    require_admin(current_user)
    get_lead_or_404(id, db, current_user)
    file = db.query(models.LeadFile).filter(models.LeadFile.id == file_id, models.LeadFile.lead_id == id, 
                        models.LeadFile.deleted_at.isnot(None)).first()

    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File must be soft-deleted before it can be permanently deleted.")

    delete_file(file.filepath)   # type: ignore
    db.delete(file)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)