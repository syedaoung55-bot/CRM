from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from ..database import get_db
from .. import schemas, models, oauth2

router = APIRouter(
    prefix="/api/v1/dashboard", 
    tags=['Dashboard']
    )

@router.get("/summary", response_model=schemas.DashboardSummaryOut)
def get_dashboard_summary(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    company_id = current_user.company_id

    total_leads = db.query(func.count(models.Lead.id)).filter(
        models.Lead.company_id == company_id, models.Lead.deleted_at.is_(None)).scalar()

    won_leads = db.query(func.count(models.Lead.id)).join(models.PipelineStage, 
        models.Lead.stage_id == models.PipelineStage.id).filter(models.Lead.company_id == company_id,
        models.PipelineStage.is_won == True, models.Lead.deleted_at.is_(None)).scalar()

    lost_leads = db.query(func.count(models.Lead.id)).join(models.PipelineStage, 
            models.Lead.stage_id == models.PipelineStage.id).filter(models.Lead.company_id == company_id,
            models.PipelineStage.is_lost == True, models.Lead.deleted_at.is_(None)).scalar()

    open_leads = total_leads - won_leads - lost_leads

    stage_counts = db.query(models.PipelineStage.name, func.count(models.Lead.id)).outerjoin(
        models.Lead, (models.Lead.stage_id == models.PipelineStage.id) & (models.Lead.deleted_at.is_(None)))\
        .filter(models.PipelineStage.company_id == company_id, ).group_by(models.PipelineStage.id, 
        models.PipelineStage.name).order_by(models.PipelineStage.order.asc()).all()

    leads_by_stage = [{"stage_name": name, "count": count} for name, count in stage_counts]

    total_tasks = db.query(func.count(models.Task.id)).join(models.Lead, 
        models.Task.lead_id == models.Lead.id).filter(models.Lead.company_id == company_id,
        models.Lead.deleted_at.is_(None), models.Task.deleted_at.is_(None)).scalar()

    completed_tasks = db.query(func.count(models.Task.id)).join(models.Lead, 
            models.Task.lead_id == models.Lead.id).filter(models.Lead.company_id == company_id,
            models.Task.is_completed == True, models.Lead.deleted_at.is_(None), 
            models.Task.deleted_at.is_(None)).scalar()

    overdue_tasks = db.query(func.count(models.Task.id)).join(models.Lead, 
                models.Task.lead_id == models.Lead.id).filter(models.Lead.company_id == company_id,
                models.Task.is_completed == False, models.Lead.deleted_at.is_(None), 
                models.Task.deleted_at.is_(None), models.Task.due_date < datetime.now(timezone.utc)).scalar()

    tasks_summary = {"total": total_tasks, "completed": completed_tasks, "overdue": overdue_tasks}

    teams = db.query(models.Team).filter(models.Team.company_id == company_id).all()
    team_performance = []
    for team in teams:
        team_total = db.query(func.count(models.Lead.id)).join(models.User,
                    models.Lead.assigned_to == models.User.id).filter(
                    models.User.team_id == team.id, models.Lead.deleted_at.is_(None)).scalar()

        team_won = db.query(func.count(models.Lead.id)).join(models.User,
                    models.Lead.assigned_to == models.User.id).join(models.PipelineStage,
                    models.Lead.stage_id == models.PipelineStage.id)\
                    .filter(models.User.team_id == team.id, models.PipelineStage.is_won == True, 
                    models.Lead.deleted_at.is_(None)).scalar()

        team_performance.append({
            "team_name": team.name, "total_leads": team_total, "won_leads": team_won
        })

    return{
        "total_leads": total_leads,
        "open_leads": open_leads,
        "won_leads": won_leads,
        "lost_leads": lost_leads,
        "leads_by_stage": leads_by_stage,
        "tasks": tasks_summary,
        "team_performance": team_performance,
    }

# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from datetime import datetime, timezone
# from ..database import get_db
# from .. import schemas, models, oauth2

# router = APIRouter(prefix="/api/v1/dashboard", tags=['Dashboard'])


# @router.get("/summary", response_model=schemas.DashboardSummaryOut)
# def get_dashboard_summary(db: Session = Depends(get_db),
#                           current_user: models.User = Depends(oauth2.get_current_user)):
#     company_id = current_user.company_id

#     # --- Lead counts ---
#     total_leads = db.query(func.count(models.Lead.id)).filter(
#         models.Lead.company_id == company_id
#     ).scalar()

#     won_leads = db.query(func.count(models.Lead.id)).join(
#         models.PipelineStage, models.Lead.stage_id == models.PipelineStage.id
#     ).filter(
#         models.Lead.company_id == company_id, models.PipelineStage.is_won == True
#     ).scalar()

#     lost_leads = db.query(func.count(models.Lead.id)).join(
#         models.PipelineStage, models.Lead.stage_id == models.PipelineStage.id
#     ).filter(
#         models.Lead.company_id == company_id, models.PipelineStage.is_lost == True
#     ).scalar()

#     open_leads = total_leads - won_leads - lost_leads

#     # --- Leads grouped by stage ---
#     stage_counts = db.query(
#         models.PipelineStage.name, func.count(models.Lead.id)
#     ).outerjoin(
#         models.Lead, models.Lead.stage_id == models.PipelineStage.id
#     ).filter(
#         models.PipelineStage.company_id == company_id
#     ).group_by(models.PipelineStage.id, models.PipelineStage.name)\
#      .order_by(models.PipelineStage.order.asc()).all()

#     leads_by_stage = [{"stage_name": name, "count": count} for name, count in stage_counts]

#     # --- Task summary ---
#     total_tasks = db.query(func.count(models.Task.id)).join(
#         models.Lead, models.Task.lead_id == models.Lead.id
#     ).filter(models.Lead.company_id == company_id).scalar()

#     completed_tasks = db.query(func.count(models.Task.id)).join(
#         models.Lead, models.Task.lead_id == models.Lead.id
#     ).filter(models.Lead.company_id == company_id, models.Task.is_compeleted == True).scalar()

#     overdue_tasks = db.query(func.count(models.Task.id)).join(
#         models.Lead, models.Task.lead_id == models.Lead.id
#     ).filter(
#         models.Lead.company_id == company_id,
#         models.Task.is_compeleted == False,
#         models.Task.due_date < datetime.now(timezone.utc)
#     ).scalar()

#     tasks_summary = {"total": total_tasks, "completed": completed_tasks, "overdue": overdue_tasks}

#     # --- Team performance ---
#     teams = db.query(models.Team).filter(models.Team.company_id == company_id).all()
#     team_performance = []
#     for team in teams:
#         team_total = db.query(func.count(models.Lead.id)).join(
#             models.User, models.Lead.assigned_to == models.User.id
#         ).filter(models.User.team_id == team.id).scalar()

#         team_won = db.query(func.count(models.Lead.id)).join(
#             models.User, models.Lead.assigned_to == models.User.id
#         ).join(
#             models.PipelineStage, models.Lead.stage_id == models.PipelineStage.id
#         ).filter(models.User.team_id == team.id, models.PipelineStage.is_won == True).scalar()

#         team_performance.append({
#             "team_name": team.name, "total_leads": team_total, "won_leads": team_won
#         })

#     return {
#         "total_leads": total_leads,
#         "open_leads": open_leads,
#         "won_leads": won_leads,
#         "lost_leads": lost_leads,
#         "leads_by_stage": leads_by_stage,
#         "tasks": tasks_summary,
#         "team_performance": team_performance,
#     }