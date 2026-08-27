from fastapi import APIRouter, Depends, status, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from datetime import datetime, timedelta, timezone
import secrets
from ..utils import utils
from ..utils.email import send_invite_email
from .. import schemas, models, oauth2
from ..permissions import require_admin

router = APIRouter(
    prefix="/api/v1/companies",
    tags = ['Companies'])



@router.get("/me", response_model=schemas.CompanyOut)
def get_my_company(current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return company

@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def user_invite(invite: schemas.UserInvite, background_tasks: BackgroundTasks, 
                  current_user: models.User = Depends(oauth2.get_current_user),db: Session = Depends(get_db)):
    require_admin(current_user)
    existing = db.query(models.User).filter(models.User.email==invite.email).first()

    if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="A user with this email already exists.")


    new_user = models.User(
        email=invite.email.lower(),
        password=utils.hash(invite.password),
        full_name=invite.full_name,
        role=invite.role,             
        company_id=current_user.company_id, 
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    verify_token = secrets.token_urlsafe(32)
    db.add(models.EmailVerificationToken(
            token = verify_token,
            user_id = new_user.id,
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        ))
    db.commit()

    db.add(models.AuditLog(
        company_id=current_user.company_id,
        table_name="users",
        record_id=new_user.id,
        field_name="role", 
        old_value=None,
        new_value=new_user.role.value,
        changed_by=current_user.id,     
    ))
    db.commit()

    background_tasks.add_task(send_invite_email,
        email=new_user.email, # type: ignore
        full_name=new_user.full_name, # type: ignore
        temp_password=invite.password,
        company_name=current_user.company.name,
        invited_by=current_user.full_name # type: ignore
    )

    return new_user