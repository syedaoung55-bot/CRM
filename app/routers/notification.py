from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import schemas, models, oauth2

router = APIRouter(
    prefix="/api/v1/notifications", 
    tags=['Notifications'])

@router.get("/", response_model=List[schemas.NotificationOut])
def get_my_notifications(unread_only: bool = False, db: Session = Depends(get_db),
                         current_user: models.User = Depends(oauth2.get_current_user)):
    query = db.query(models.Notification).filter(models.Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.Notification.is_read == False)

    return query.order_by(models.Notification.created_at.desc()).all()

@router.patch("/{id}/read", response_model=schemas.NotificationOut)
def mark_notification_read(id: int, db: Session = Depends(get_db),
                           current_user: models.User = Depends(oauth2.get_current_user)):
    notification = db.query(models.Notification).filter(
        models.Notification.id == id, models.Notification.user_id == current_user.id
    ).first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification with id {id} is not found.")

    notification.is_read = True # type: ignore
    db.commit()
    db.refresh(notification)
    return notification

@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id, models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)