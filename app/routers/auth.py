from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

from ..utils import utils
from ..database import get_db
from .. import schemas, models, oauth2

router = APIRouter(
    prefix = "/api/v1/auth",
    tags = ['Authentication'])


@router.post("/login", response_model=schemas.Token)
def user_login(user_credentials: OAuth2PasswordRequestForm=Depends(),
               db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.username.lower()).first()
    
    if not user or not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials.")
    
    acces_token = oauth2.create_access_token(data={"user_id": user.id, "company_id": user.company_id})
    refresh_token = oauth2.create_refresh_token()
    oauth2.save_refresh_token(user.id, refresh_token, db) # type: ignore
    return {"access_token": acces_token, "refresh_token": refresh_token, "token_type": "bearer", 
            "company_id": user.company_id, "company_name": user.company.name, "role": user.role.value}

@router.post("/refresh", response_model=schemas.Token)
def refreshed_token(ref_token: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    db_token = oauth2.verify_refresh_token(ref_token.refresh_token, db)
    user = db.query(models.User).filter(models.User.id == db_token.user_id).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials.")
    
    oauth2.revoke_refresh_token(ref_token.refresh_token, db)

    new_acces_token = oauth2.create_access_token(data={"user_id": user.id, "company_id": user.company_id})
    new_refresh_token = oauth2.create_refresh_token()
    oauth2.save_refresh_token(user.id, new_refresh_token, db) # type: ignore

    return {"access_token": new_acces_token, "refresh_token": new_refresh_token, "token_type": "bearer",
         "company_id": user.company_id, "company_name": user.company.name, "role": user.role.value}

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(ref_token: schemas.RefreshTokenRequest, db: Session = Depends(get_db),
            current_user: models.User = Depends(oauth2.get_current_user)):
    
    oauth2.revoke_refresh_token(ref_token.refresh_token, db)