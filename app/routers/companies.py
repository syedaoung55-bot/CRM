from fastapi import APIRouter, Depends, status, Response, HTTPException
from sqlalchemy.orm import Session
from ..utils.email import send_lead_assigned_email
from ..database import get_db
from typing import Optional, List
import secrets
from ..utils import utils
from ..utils.email import send_invite_email
from .. import schemas, models, oauth2
from ..permissions import (get_lead_or_404, check_lead_permission, check_lead_view_permission,
                           require_admin, require_admin_or_manager, create_activity_log)

router = APIRouter(
    prefix="/api/v1/companies",
    tags = ['Companies'])


# @router.post("/", response_model=schemas.CompanyOut, status_code=201)
# def create_company(company_in: schemas.CompanyCreate,db: Session = Depends(get_db),
#     current_user: models.User = Depends(oauth2.get_current_user) ):
#     require_admin(current_user)
#     new_company = models.Company(
#         name=company_in.name
#     )
#     db.add(new_company)
#     db.commit()
#     db.refresh(new_company)
#     return new_company

@router.get("/me", response_model=schemas.CompanyOut)
def get_my_company(current_user: models.User = Depends(oauth2.get_current_user), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return company

@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def user_invite(invite: schemas.UserInvite, current_user: models.User = Depends(oauth2.get_current_user),
                 db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email==invite.email).first()

    if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail="A user with this email already exists.")

    temp_password = secrets.token_urlsafe(9)

    new_user = models.User(
        email=invite.email.lower(),
        password=utils.hash(temp_password),
        full_name=invite.full_name,
        role=invite.role,             
        company_id=current_user.company_id, 
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await send_invite_email(
        email=new_user.email, # type: ignore
        full_name=new_user.full_name, # type: ignore
        temp_password=temp_password,
        company_name=current_user.company.name,
        invited_by=current_user.full_name # type: ignore
    )

    return new_user