from app import models
from datetime import datetime, timezone


def test_get_notifications_unauthenticated(client):
    res = client.get("/api/v1/notifications")
    assert res.status_code == 401


def test_get_notifications_empty(sales_client):
    res = sales_client.get("/api/v1/notifications")
    assert res.status_code == 200
    assert res.json() == []


def test_get_notifications_returns_own_only(sales_client, test_sales, test_admin, test_lead, session):
    session.add_all([
        models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                            message="For sales", lead_id=test_lead.id),
        models.Notification(user_id=test_admin.id, type=models.NotificationType.assignment.value,
                            message="For admin", lead_id=test_lead.id),
    ])
    session.commit()

    res = sales_client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["message"] == "For sales"


def test_get_notifications_unread_only_filter(sales_client, test_sales, test_lead, session):
    session.add_all([
        models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                            message="Unread", lead_id=test_lead.id, is_read=False),
        models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                            message="Read", lead_id=test_lead.id, is_read=True),
    ])
    session.commit()

    res = sales_client.get("/api/v1/notifications?unread_only=true")
    data = res.json()
    assert len(data) == 1
    assert data[0]["message"] == "Unread"


def test_get_notifications_ordered_newest_first(sales_client, test_sales, test_lead, session):
    session.add(models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                                    message="First", lead_id=test_lead.id))
    session.commit()

    session.add(models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                                    message="Second", lead_id=test_lead.id))
    session.commit()

    res = sales_client.get("/api/v1/notifications")
    assert res.json()[0]["message"] == "Second"


def test_mark_notification_read_success(sales_client, test_sales, test_lead, session):
    notif = models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                                message="Mark me", lead_id=test_lead.id)
    session.add(notif)
    session.commit()
    session.refresh(notif)

    res = sales_client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert res.status_code == 200
    assert res.json()["is_read"] is True


def test_mark_notification_read_not_found(sales_client):
    res = sales_client.patch("/api/v1/notifications/9999/read")
    assert res.status_code == 404


def test_mark_notification_read_not_owned_returns_404(sales_client, test_admin, test_lead, session):
    notif = models.Notification(user_id=test_admin.id, type=models.NotificationType.assignment.value,
                                message="Not yours", lead_id=test_lead.id)
    session.add(notif)
    session.commit()
    session.refresh(notif)

    res = sales_client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert res.status_code == 404


def test_mark_notification_read_unauthenticated(client, test_sales, test_lead, session):
    notif = models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                                message="test", lead_id=test_lead.id)
    session.add(notif)
    session.commit()
    session.refresh(notif)

    res = client.patch(f"/api/v1/notifications/{notif.id}/read")
    assert res.status_code == 401


def test_mark_all_read_success(sales_client, test_sales, test_lead, session):
    session.add_all([
        models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                            message="A", lead_id=test_lead.id, is_read=False),
        models.Notification(user_id=test_sales.id, type=models.NotificationType.assignment.value,
                            message="B", lead_id=test_lead.id, is_read=False),
    ])
    session.commit()

    res = sales_client.patch("/api/v1/notifications/read-all")
    assert res.status_code == 204

    remaining_unread = session.query(models.Notification).filter(
        models.Notification.user_id == test_sales.id, models.Notification.is_read == False
    ).count()
    assert remaining_unread == 0


def test_mark_all_read_does_not_affect_other_users(sales_client, test_sales, test_admin, test_lead, session):
    session.add(models.Notification(user_id=test_admin.id, type=models.NotificationType.assignment.value,
                                    message="admin unread", lead_id=test_lead.id, is_read=False))
    session.commit()

    sales_client.patch("/api/v1/notifications/read-all")

    admin_notif = session.query(models.Notification).filter(models.Notification.user_id == test_admin.id).first()
    assert admin_notif.is_read is False


def test_mark_all_read_unauthenticated(client):
    res = client.patch("/api/v1/notifications/read-all")
    assert res.status_code == 401


def test_mark_all_read_empty_no_error(sales_client):
    res = sales_client.patch("/api/v1/notifications/read-all")
    assert res.status_code == 204



def test_search_unauthenticated(client):
    res = client.get("/api/v1/search?q=test")
    assert res.status_code == 401


def test_search_query_too_short(sales_client):
    res = sales_client.get("/api/v1/search?q=a")
    assert res.status_code == 200
    data = res.json()
    assert data["lead"] == []
    assert data["user"] == []
    assert data["task"] == []
    assert data["company"] == []


def test_search_missing_query_param(sales_client):
    res = sales_client.get("/api/v1/search")
    assert res.status_code == 422


def test_search_finds_lead_by_name(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/search?q={test_lead.name[:3]}")
    assert res.status_code == 200
    ids = [l["id"] for l in res.json()["lead"]]
    assert test_lead.id in ids


def test_search_finds_lead_by_email(sales_client, test_lead):
    res = sales_client.get("/api/v1/search?q=ali@test")
    ids = [l["id"] for l in res.json()["lead"]]
    assert test_lead.id in ids


def test_search_finds_lead_by_company_name(sales_client, test_lead):
    res = sales_client.get("/api/v1/search?q=ABC")
    ids = [l["id"] for l in res.json()["lead"]]
    assert test_lead.id in ids


def test_search_excludes_soft_deleted_leads(sales_client, test_lead, session):
    test_lead.deleted_at = datetime.now(timezone.utc)
    session.commit()

    res = sales_client.get(f"/api/v1/search?q={test_lead.name[:3]}")
    ids = [l["id"] for l in res.json()["lead"]]
    assert test_lead.id not in ids


def test_search_finds_user_by_full_name(sales_client, test_admin):
    res = sales_client.get(f"/api/v1/search?q={test_admin.full_name[:4]}")
    ids = [u["id"] for u in res.json()["user"]]
    assert test_admin.id in ids


def test_search_finds_user_by_email(sales_client, test_admin):
    res = sales_client.get("/api/v1/search?q=admin@test")
    ids = [u["id"] for u in res.json()["user"]]
    assert test_admin.id in ids


def test_search_finds_own_company(sales_client, test_company):
    res = sales_client.get(f"/api/v1/search?q={test_company.name[:4]}")
    ids = [c["id"] for c in res.json()["company"]]
    assert test_company.id in ids


def test_search_does_not_find_other_company(sales_client, test_company_2):
    res = sales_client.get(f"/api/v1/search?q={test_company_2.name}")
    ids = [c["id"] for c in res.json()["company"]]
    assert test_company_2.id not in ids


def test_search_finds_task_by_title(sales_client, test_lead, session):
    task = models.Task(title="Unique Followup Task", lead_id=test_lead.id, priority=models.TaskPriority.medium)
    session.add(task)
    session.commit()
    session.refresh(task)

    res = sales_client.get("/api/v1/search?q=Followup")
    ids = [t["id"] for t in res.json()["task"]]
    assert task.id in ids


def test_search_excludes_deleted_tasks(sales_client, test_lead, session):
    task = models.Task(title="Deleted Search Task", lead_id=test_lead.id, priority=models.TaskPriority.medium,
                       deleted_at=datetime.now(timezone.utc))
    session.add(task)
    session.commit()

    res = sales_client.get("/api/v1/search?q=Deleted")
    ids = [t["id"] for t in res.json()["task"]]
    assert task.id not in ids


def test_search_excludes_other_company_leads(sales_client, test_company_2, test_admin_company2, session):
    other_lead = models.Lead(name="ZZZUniqueOtherCoLead", owner_id=test_admin_company2.id,
                             company_id=test_company_2.id)
    session.add(other_lead)
    session.commit()

    res = sales_client.get("/api/v1/search?q=ZZZUniqueOtherCoLead")
    assert res.json()["lead"] == []


def test_search_no_results(sales_client):
    res = sales_client.get("/api/v1/search?q=zzznomatch12345")
    data = res.json()
    assert data == {"lead": [], "user": [], "task": [], "company": []}


def test_search_respects_max_results_per_type(sales_client, test_sales, test_company, session):
    for i in range(15):
        session.add(models.Lead(name=f"Bulk Lead {i}", owner_id=test_sales.id, company_id=test_company.id))
    session.commit()

    res = sales_client.get("/api/v1/search?q=Bulk Lead")
    assert len(res.json()["lead"]) == 10