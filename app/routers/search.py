from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, oauth2

router = APIRouter(
    prefix="/api/v1/search", 
    tags=['Search']
    )

MAX_RESULTS_PER_TYPE = 10

@router.get("/", response_model=schemas.GlobalSearchOut)
def global_search(q: str, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):

    if not q or len(q.strip()) < 2:
        return {"lead": [], "user": [], "task": [], "company": []}

    like_pattren = f"%{q.strip()}%"
    company_id = current_user.company_id

    leads = db.query(models.Lead).filter(models.Lead.company_id == company_id,
                    models.Lead.deleted_at.is_(None),
                    (models.Lead.name.ilike(like_pattren)) | 
                    (models.Lead.email.ilike(like_pattren)) | 
                    (models.Lead.company.ilike(like_pattren))
                    ).limit(MAX_RESULTS_PER_TYPE).all()

    users = db.query(models.User).filter(models.User.company_id == company_id,
                    (models.User.full_name.ilike(like_pattren)) | 
                    (models.User.email.ilike(like_pattren))
                    ).limit(MAX_RESULTS_PER_TYPE).all()

    companies = db.query(models.Company).filter(models.Company.id == company_id,
                    (models.Company.name.ilike(like_pattren))
                    ).limit(MAX_RESULTS_PER_TYPE).all()

    tasks = db.query(models.Task).join(models.Lead, models.Task.lead_id == models.Lead.id)\
                    .filter(models.Lead.company_id == company_id,
                    models.Lead.deleted_at.is_(None),
                    models.Task.deleted_at.is_(None), 
                    (models.Task.title.ilike(like_pattren))
                    ).limit(MAX_RESULTS_PER_TYPE).all()

    return {"lead": leads, "user": users, "task": tasks, "company": companies}