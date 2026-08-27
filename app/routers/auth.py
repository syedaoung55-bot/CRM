from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
import secrets
from datetime import timedelta, timezone, datetime
from ..utils import utils, email
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

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(request: schemas.PasswordResetRequest, background_tasks: BackgroundTasks, 
                    db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.email == request.email.lower()).first()

    if user:
        reset_token = secrets.token_urlsafe(32)
        db.add(models.PasswordResetToken(
            token = reset_token, user_id = user.id,
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        ))
        db.commit()

        background_tasks.add_task(email.send_password_reset_email, email = str(user.email), # type: ignore
                              full_name = str(user.full_name), reset_token = reset_token) # type: ignore

    return {"detail": "If an account with that email exists, a reset link has been sent."}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(request: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):

    reset_record = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == request.token).first()

    if not reset_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail="Invalid or expired reset token.")
    
    if reset_record.is_used: # type: ignore
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="This reset token has already been used.")
    
    if reset_record.expires_at < datetime.now(timezone.utc): # type: ignore
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="This reset token has expired.")

    user = db.query(models.User).filter(models.User.id == reset_record.user_id).first()
    user.password = utils.hash(request.new_password) # type: ignore
    reset_record.is_used = True # type: ignore
    db.commit()

    return {"detail": "Password has been reset successfully."}

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    record = db.query(models.EmailVerificationToken).filter(
                    models.EmailVerificationToken.token == token).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Invalid verification token.")
    
    if record.expires_at < datetime.now(timezone.utc): # type: ignore
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                            detail="Verification token has expired.")

    user = db.query(models.User).filter(models.User.id == record.user_id).first()
    user.is_verified = True # type: ignore
    db.delete(record)
    db.commit()

    return {"detail": "Email verified successfully."}

@router.get("/sessions", response_model=List[schemas.SessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    return db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == current_user.id,
        models.RefreshToken.is_revoked == False,
        models.RefreshToken.expires_at > datetime.now(timezone.utc)
    ).order_by(models.RefreshToken.created_at.desc()).all()


@router.post("/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT)
def revoke_all_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == current_user.id,
                         models.RefreshToken.is_revoked == False).update({"is_revoked": True})
    
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    session = db.query(models.RefreshToken).filter(
        models.RefreshToken.id == session_id, models.RefreshToken.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session with id {session_id} is not found.")

    session.is_revoked = True # type: ignore
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)