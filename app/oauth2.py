from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from . import schemas, database, models
from fastapi import Depends, status, HTTPException
from .config import settings
import secrets
from sqlalchemy.orm import Session
from fastapi.security.oauth2 import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt

def create_refresh_token():

    return secrets.token_urlsafe(64)

def save_refresh_token(user_id: int, token: str, db: Session):
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    db_token = models.RefreshToken(
        token = token,
        user_id = user_id,
        expires_at = expires_at,
        is_revoked = False
    )
    db.add(db_token)
    db.commit()

def verify_refresh_token(token: str, db:Session):
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()

    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid refresh token.")
    
    if db_token.is_revoked: # type: ignore
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token has been revoked.")
    
    if db_token.expires_at < datetime.now(timezone.utc): # type: ignore
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token has expired.")
    
    return db_token

def revoke_refresh_token(token: str, db: Session):
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()

    if db_token:
        db_token.is_revoked = True  # type: ignore
        db.commit()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials", headers={"WWW-Authenticte": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id") # type: ignore
        company_id: int = payload.get("company_id") # type: ignore
        if user_id is None or company_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user