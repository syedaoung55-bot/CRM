from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from ..utils.email import send_welcome_email
from ..utils import utils
from ..database import get_db
from .. import schemas, models

router = APIRouter(
    prefix = "/auth",
    tags = ['User'])

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.UserOut)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_dict = user.model_dump()
    user_dict['password'] = utils.hash(user.password)
    new_user = models.User(**user_dict)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    await send_welcome_email(
        email = str(new_user.email),
        full_name = str(new_user.full_name)
    )
    
    return new_user