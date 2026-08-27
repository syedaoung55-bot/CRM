from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, models, oauth2
from ..permissions import get_lead_or_404, check_lead_permission, scoped

router = APIRouter(
    prefix="/api/v1", 
    tags=['Tags']
    )

@router.post("/tags", status_code=status.HTTP_201_CREATED, response_model=schemas.TagOut)
def create_tag(tag: schemas.TagCreate, db: Session=Depends(get_db), 
                current_user: models.User =Depends(oauth2.get_current_user)):
    existing = db.query(models.Tag).filter(models.Tag.company_id == current_user.company_id,
                                           models.Tag.name.ilike(tag.name)).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Tag '{tag.name}' already exists.")

    new_tag = models.Tag(
        name = tag.name,
        company_id = current_user.company_id
    )

    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)

    return new_tag

@router.get("/tags", response_model=List[schemas.TagOut])
def get_all_tag(db: Session=Depends(get_db), current_user: models.User =Depends(oauth2.get_current_user)):

    return scoped(db.query(models.Tag), models.Tag, current_user).all()

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id:int, db: Session=Depends(get_db), current_user: models.User =Depends(oauth2.get_current_user)):

    tag = scoped(db.query(models.Tag), models.Tag, current_user).filter(models.Tag.id == tag_id).first()

    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Tag with '{tag_id}' not found.")

    db.delete(tag)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/leads/{id}/tags/{tag_id}", response_model=schemas.LeadOut)
def add_tag_to_lead(id: int, tag_id: int, db: Session = Depends(get_db),
                    current_user: models.User = Depends(oauth2.get_current_user)):

    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    tag = scoped(db.query(models.Tag), models.Tag, current_user).filter(models.Tag.id == tag_id).first()
    if not tag: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Tag with '{tag_id}' not found.")

    if tag in lead.tags:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Lead already has this Tag.")

    lead.tags.append(tag)
    db.commit()
    db.refresh(lead)

    return lead

@router.delete("/leads/{id}/tags/{tag_id}", response_model=schemas.LeadOut)
def remove_tag_from_lead(id: int, tag_id: int, db: Session = Depends(get_db),
                    current_user: models.User = Depends(oauth2.get_current_user)):

    lead = get_lead_or_404(id, db, current_user)
    check_lead_permission(lead, current_user, db)

    tag = scoped(db.query(models.Tag), models.Tag, current_user).filter(models.Tag.id == tag_id).first()
    if not tag or tag not in lead.tags: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Lead does not have this Tag.")

    lead.tags.remove(tag)
    db.commit()
    db.refresh(lead)

    return lead