from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, models, oauth2
from ..permissions import require_admin, scoped, log_field_changes

router = APIRouter(
    prefix="/api/v1/pipeline-stages",
    tags = ['Pipeline Stages'])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PipelineStageOut)
def create_stage(stage: schemas.PipelineStageCreate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    new_stage = models.PipelineStage(**stage.model_dump(), company_id=current_user.company_id)
    db.add(new_stage)
    db.commit()
    db.refresh(new_stage)
    return new_stage

@router.get("/", response_model=List[schemas.PipelineStageOut])
def get_all_stages(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    return scoped(db.query(models.PipelineStage), models.PipelineStage, current_user
                  ).order_by(models.PipelineStage.order.asc()).all()

@router.put("/{id}", response_model=schemas.PipelineStageOut)
def update_stage(id: int, stage_update: schemas.PipelineStageUpdate, db: Session = Depends(get_db),
                 current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    stage = scoped(db.query(models.PipelineStage), models.PipelineStage, current_user
                   ).filter(models.PipelineStage.id == id).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stage with id {id} is not found.")

    updated_data = stage_update.model_dump(exclude_unset=True)

    before = {field: getattr(stage, field) for field in updated_data}

    for field, value in updated_data.items():
        setattr(stage, field, value)
    db.commit()
    db.refresh(stage)

    after = {field: getattr(stage, field) for field in updated_data}

    log_field_changes(db, "Stages", stage.id, before, after, current_user.id, current_user.company_id) #type: ignore
    return stage

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)

    stage = scoped(db.query(models.PipelineStage), models.PipelineStage, current_user
                   ).filter(models.PipelineStage.id == id).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stage with id {id} is not found.")

    leads_using_it = db.query(models.Lead).filter(models.Lead.stage_id == id).count()
    if leads_using_it > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot delete: {leads_using_it} lead(s) are currently in this stage.")

    db.delete(stage)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)