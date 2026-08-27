import asyncio
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from ..database import sessionlocal
from .. import models
from ..permissions import create_notification
from ..utils.email import weekly_summary_email

logger = logging.getLogger("crm.scheduler")


def check_overdure_tasks():
    db = sessionlocal()

    try:
        overdue = db.query(models.Task).join(models.Lead, models.Task.lead_id == models.Lead.id)\
        .filter(models.Task.is_completed == False, models.Task.deleted_at.is_(None),
                models.Lead.deleted_at.is_(None), models.Task.due_date.isnot(None),
                models.Task.due_date < datetime.now(timezone.utc)).all()

        for task in overdue:
            if task.assignee:
                create_notification(
                    db = db,
                    user_id = task.assignee.id,
                    type = models.NotificationType.task_assignment.value,
                    message = f"Task {task.title} is overdue.",
                    lead_id = task.lead_id # type: ignore
                )
        db.commit()

        logger.info(f"Overdue task check complete: {len(overdue)} overdue tasks found.")

    except Exception:
        db.rollback()
        logger.exception("check_overdue_tasks failed.")

    finally:
        db.close()

def send_weekly_summary():
    db = sessionlocal()

    try:
        companies = db.query(models.Company).all()
        
        for company in companies:
            admins = db.query(models.User).filter(models.User.company_id == company.id,
                                            models.User.role == models.UserRole.admin).all()

            open_leads = db.query(models.Lead).filter(models.Lead.company_id == company.id,
                                            models.Lead.deleted_at.is_(None)).count()

            for admin in admins:
                if admin.email: # type: ignore
                    asyncio.run(weekly_summary_email(
                        email = str(admin.email),
                        full_name = str(admin.full_name),
                        company_name = str(company.name),
                        open_leads = open_leads
                    ))
            logger.info("Weekly summary email sent.")

    except Exception:
        db.rollback()
        logger.exception("send_weekly_summary failed.")

    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_overdure_tasks, "interval", hours=1, id="check_overdue_tasks")
scheduler.add_job(send_weekly_summary, "cron", day_of_week="mon", hour=8, minute=0, id="Weekly_summary")