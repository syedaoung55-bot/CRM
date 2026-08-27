from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from .. import schemas, models, oauth2
from ..permissions import require_admin, scoped

router = APIRouter(prefix="/api/v1/audit-logs", tags=['Audit Logs'])


@router.get("/", response_model=List[schemas.AuditLogOut])
def get_audit_logs(table_name: Optional[str] = None, record_id: Optional[int] = None,
                   db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    require_admin(current_user)
    
    query = scoped(db.query(models.AuditLog), models.AuditLog, current_user)

    if table_name:
        query = query.filter(models.AuditLog.table_name == table_name)
    if record_id:
        query = query.filter(models.AuditLog.record_id == record_id)

    return query.order_by(models.AuditLog.created_at.desc()).all()