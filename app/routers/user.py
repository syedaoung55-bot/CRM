from ..utils.email import send_welcome_email, send_verification_email
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..utils import utils
import secrets
from datetime import timedelta, datetime, timezone
from ..database import get_db
from .. import schemas, models

router = APIRouter(
    prefix = "/api/v1/auth",
    tags = ['User'])

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, background_tasks: BackgroundTasks,  db: Session = Depends(get_db),):
    existing = db.query(models.User).filter(models.User.email == user.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="An account with this email already exists.")

    try:
        new_company = models.Company(name=user.company_name)
        db.add(new_company)
        db.flush()

        new_user = models.User(
            email=user.email.lower(),
            password=utils.hash(user.password),
            full_name=user.full_name,
            role=models.UserRole.admin,
            is_active=True,
            company_id=new_company.id,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    verify_token = secrets.token_urlsafe(32)
    db.add(models.EmailVerificationToken(
        token = verify_token,
        user_id = new_user.id,
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    ))
    db.commit()
    
    background_tasks.add_task(send_welcome_email, email=str(new_user.email), full_name=str(new_user.full_name))
    return new_user