from unittest.mock import patch, AsyncMock
from app import models


# TAGS — CREATE


def test_create_tag_admin_success(admin_client):
    res = admin_client.post("/api/v1/tags", json={"name": "hot"})
    assert res.status_code == 201
    assert res.json()['name'] == "hot"


def test_create_tag_sales_allowed(sales_client):
    res = sales_client.post("/api/v1/tags", json={"name": "sales-made-tag"})
    assert res.status_code == 201


def test_create_tag_manager_allowed(manager_client):
    res = manager_client.post("/api/v1/tags", json={"name": "manager-made-tag"})
    assert res.status_code == 201


def test_create_tag_duplicate_case_insensitive_rejected(admin_client):
    admin_client.post("/api/v1/tags", json={"name": "urgent"})
    res = admin_client.post("/api/v1/tags", json={"name": "URGENT"})
    assert res.status_code == 400


def test_create_tag_same_name_different_company_allowed(admin_client, session, test_company_2):
    admin_client.post("/api/v1/tags", json={"name": "shared-name"})
    other_tag = models.Tag(name="shared-name", company_id=test_company_2.id)
    session.add(other_tag)
    session.commit()   
    assert other_tag.id is not None


def test_create_tag_unauthenticated(client):
    res = client.post("/api/v1/tags", json={"name": "no auth"})
    assert res.status_code == 401


def test_create_tag_missing_name(admin_client):
    res = admin_client.post("/api/v1/tags", json={})
    assert res.status_code == 422


def test_create_tag_company_id_set_automatically(admin_client, test_company):
    res = admin_client.post("/api/v1/tags", json={"name": "scoped tag"})
    assert res.json()['company_id'] == test_company.id



# TAGS — GET ALL


def test_get_all_tags(admin_client, session, test_company):
    session.add(models.Tag(name="listed", company_id=test_company.id))
    session.commit()
    res = admin_client.get("/api/v1/tags")
    assert res.status_code == 200
    assert any(t['name'] == "listed" for t in res.json())


def test_get_all_tags_excludes_other_company(admin_client, session, test_company_2):
    session.add(models.Tag(name="foreign", company_id=test_company_2.id))
    session.commit()
    res = admin_client.get("/api/v1/tags")
    assert not any(t['name'] == "foreign" for t in res.json())


def test_get_all_tags_sales_allowed(sales_client):
    res = sales_client.get("/api/v1/tags")
    assert res.status_code == 200


def test_get_all_tags_unauthenticated(client):
    res = client.get("/api/v1/tags")
    assert res.status_code == 401


def test_get_all_tags_empty(admin_client):
    res = admin_client.get("/api/v1/tags")
    assert res.status_code == 200
    assert isinstance(res.json(), list)



# TAGS — DELETE


def test_delete_tag_success(admin_client, session, test_company):
    tag = models.Tag(name="deletable", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.delete(f"/api/v1/tags/{tag.id}")
    assert res.status_code == 204


def test_delete_tag_sales_allowed(sales_client, session, test_company):
    tag = models.Tag(name="sales can delete", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = sales_client.delete(f"/api/v1/tags/{tag.id}")
    assert res.status_code == 204


def test_delete_tag_not_found(admin_client):
    res = admin_client.delete("/api/v1/tags/9999")
    assert res.status_code == 404


def test_delete_tag_cross_company_rejected(admin2_client, session, test_company):
    tag = models.Tag(name="not yours", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin2_client.delete(f"/api/v1/tags/{tag.id}")
    assert res.status_code == 404


def test_delete_tag_unauthenticated(client, session, test_company):
    tag = models.Tag(name="auth check", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = client.delete(f"/api/v1/tags/{tag.id}")
    assert res.status_code == 401


def test_delete_tag_actually_removed(admin_client, session, test_company):
    tag = models.Tag(name="gone after delete", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    tag_id = tag.id

    admin_client.delete(f"/api/v1/tags/{tag_id}")
    row = session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    assert row is None   



# TAGS — ATTACH TO LEAD


def test_add_tag_to_lead_success(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="hot", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 200
    assert any(t['id'] == tag.id for t in res.json()['tags'])


def test_add_tag_to_lead_owner_allowed(sales_client, test_lead, session, test_company):
    tag = models.Tag(name="owner add", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 200


def test_add_tag_to_lead_non_owner_forbidden(sales2_client, test_lead, session, test_company):
    tag = models.Tag(name="non owner", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = sales2_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 403


def test_add_tag_to_lead_tag_not_found(admin_client, test_lead):
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/9999")
    assert res.status_code == 404


def test_add_tag_to_lead_from_other_company_rejected(admin_client, test_lead, session, test_company_2):
    foreign_tag = models.Tag(name="foreign", company_id=test_company_2.id)
    session.add(foreign_tag)
    session.commit()
    session.refresh(foreign_tag)

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{foreign_tag.id}")
    assert res.status_code == 404


def test_add_duplicate_tag_to_lead_rejected(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="dup", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 400


def test_add_tag_to_lead_not_found(admin_client, session, test_company):
    tag = models.Tag(name="orphan tag", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.post(f"/api/v1/leads/9999/tags/{tag.id}")
    assert res.status_code == 404


def test_add_tag_to_lead_unauthenticated(client, test_lead, session, test_company):
    tag = models.Tag(name="auth needed", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 401



# TAGS — REMOVE FROM LEAD


def test_remove_tag_from_lead_success(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="removable", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 200
    assert not any(t['id'] == tag.id for t in res.json()['tags'])


def test_remove_tag_not_currently_on_lead(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="never attached", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 404


def test_remove_tag_from_lead_non_owner_forbidden(sales2_client, test_lead, admin_client, session, test_company):
    tag = models.Tag(name="protected", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    res = sales2_client.delete(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 403


def test_remove_tag_tag_id_not_found(admin_client, test_lead):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tags/9999")
    assert res.status_code == 404


def test_remove_tag_lead_not_found(admin_client, session, test_company):
    tag = models.Tag(name="orphan removal", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.delete(f"/api/v1/leads/9999/tags/{tag.id}")
    assert res.status_code == 404



# TASKS — CREATE


def test_create_task_success(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "Follow up call", "priority": "high"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['title'] == "Follow up call"
    assert data['priority'] == "high"
    assert data['is_completed'] is False


def test_create_task_default_priority(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "no priority"})
    assert res.status_code == 201
    assert res.json()['priority'] == "medium"


def test_create_task_with_due_date(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "deadline task", "due_date": "2026-12-01T10:00:00Z"
    })
    assert res.status_code == 201
    assert res.json()['due_date'] is not None


def test_create_task_with_assignee(sales_client, test_lead, test_sales):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "assigned task", "assigned_to": test_sales.id
    })
    assert res.status_code == 201
    assert res.json()['assigned_to'] == test_sales.id


def test_create_task_assignee_not_found(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "bad assignee", "assigned_to": 9999
    })
    assert res.status_code == 404


def test_create_task_assignee_cross_company_rejected(sales_client, test_lead, test_admin_company2):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "cross company assignee", "assigned_to": test_admin_company2.id
    })
    assert res.status_code == 404


def test_create_task_lead_not_found(sales_client):
    res = sales_client.post("/api/v1/leads/9999/tasks", json={"title": "orphan task"})
    assert res.status_code == 404


def test_create_task_missing_title(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={})
    assert res.status_code == 422


def test_create_task_unauthenticated(client, test_lead):
    res = client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "no auth"})
    assert res.status_code == 401


def test_create_task_non_owner_forbidden(sales2_client, test_lead):
    res = sales2_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "not my lead"})
    assert res.status_code == 403


def test_create_task_activity_log(sales_client, test_lead, session):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "logged task"})
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "Task Created").first()
    assert log is not None


def test_create_task_assignment_creates_notification(sales_client, test_lead, test_sales2, session, test_company):
    test_sales2.company_id = test_company.id
    session.commit()

    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "notify test", "assigned_to": test_sales2.id
    })
    notif = session.query(models.Notification).filter(
        models.Notification.user_id == test_sales2.id,
        models.Notification.type == models.NotificationType.task_assignment.value
    ).first()
    assert notif is not None


def test_create_task_self_assignment_creates_no_notification(sales_client, test_lead, test_sales, session):
    session.query(models.Notification).delete()
    session.commit()

    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "self assign", "assigned_to": test_sales.id
    })
    notif = session.query(models.Notification).filter(
        models.Notification.type == models.NotificationType.task_assignment.value
    ).first()
    assert notif is None



# TASKS — GET (note: full check_lead_permission, not view-only)


def test_get_tasks_success(sales_client, test_lead):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "task 1"})
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_get_tasks_empty(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    assert res.status_code == 200
    assert res.json() == []


def test_get_tasks_lead_not_found(sales_client):
    res = sales_client.get("/api/v1/leads/9999/tasks")
    assert res.status_code == 404


def test_get_tasks_unauthenticated(client, test_lead):
    res = client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    assert res.status_code == 401


def test_get_tasks_non_owner_forbidden(sales2_client, test_lead):
    res = sales2_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    assert res.status_code == 403


def test_get_tasks_admin_can_view_any_lead(admin_client, test_lead):
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    assert res.status_code == 200


def test_get_tasks_excludes_soft_deleted(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "to be deleted"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    ids = [t["id"] for t in res.json()]
    assert task_id not in ids


def test_get_tasks_ordered_by_due_date(sales_client, test_lead):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "later", "due_date": "2026-12-31T00:00:00Z"
    })
    sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "sooner", "due_date": "2026-01-01T00:00:00Z"
    })
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    titles_with_dates = [t['title'] for t in res.json() if t['due_date']]
    assert titles_with_dates[0] == "sooner"



# TASKS — GET DELETED (admin only)


def test_get_deleted_tasks_admin_only(admin_client, sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "to delete"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res_admin = admin_client.get(f"/api/v1/leads/{test_lead.id}/tasks/deleted")
    assert res_admin.status_code == 200
    assert any(t['id'] == task_id for t in res_admin.json())

    res_sales = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks/deleted")
    assert res_sales.status_code == 403



# TASKS — UPDATE


def test_update_task_mark_completed(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "to complete"})
    task_id = create_res.json()['id']

    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"is_completed": True})
    assert res.status_code == 200
    assert res.json()['is_completed'] is True


def test_update_task_partial_update_preserves_other_fields(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "original title", "priority": "high"
    })
    task_id = create_res.json()['id']

    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"is_completed": True})
    assert res.json()['title'] == "original title"
    assert res.json()['priority'] == "high"


def test_update_task_reassign_creates_notification(sales_client, test_lead, test_sales2, session, test_company):
    test_sales2.company_id = test_company.id
    session.commit()

    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "reassign me"})
    task_id = create_res.json()['id']
    session.query(models.Notification).delete()
    session.commit()

    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"assigned_to": test_sales2.id})
    assert res.status_code == 200

    notif = session.query(models.Notification).filter(
        models.Notification.user_id == test_sales2.id,
        models.Notification.type == models.NotificationType.task_assignment.value
    ).first()
    assert notif is not None


def test_update_task_same_assignee_no_duplicate_notification(sales_client, test_lead, test_sales, session):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "already assigned", "assigned_to": test_sales.id
    })
    task_id = create_res.json()['id']
    session.query(models.Notification).delete()
    session.commit()

    sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"assigned_to": test_sales.id})
    count = session.query(models.Notification).filter(
        models.Notification.type == models.NotificationType.task_assignment.value
    ).count()
    assert count == 0


def test_update_task_reassign_cross_company_rejected(sales_client, test_lead, test_admin_company2):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "reassign attempt"})
    task_id = create_res.json()['id']

    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={
        "assigned_to": test_admin_company2.id
    })
    assert res.status_code == 404


def test_update_task_not_found(sales_client, test_lead):
    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/9999", json={"is_completed": True})
    assert res.status_code == 404


def test_update_task_wrong_lead_id_paired(sales_client, test_lead, test_lead_admin, admin_client):
    create_res = admin_client.post(f"/api/v1/leads/{test_lead_admin.id}/tasks", json={"title": "cross lead"})
    task_id = create_res.json()['id']

    res = sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"is_completed": True})
    assert res.status_code == 404


def test_update_task_non_owner_forbidden(sales2_client, test_lead):
    res = sales2_client.put(f"/api/v1/leads/{test_lead.id}/tasks/1", json={"is_completed": True})
    assert res.status_code == 403


def test_update_task_creates_audit_log(sales_client, test_lead, session):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "audit me", "priority": "low"
    })
    task_id = create_res.json()['id']

    sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"priority": "high"})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "tasks", models.AuditLog.record_id == task_id,
        models.AuditLog.field_name == "priority"
    ).first()
    assert audit is not None


def test_update_task_same_value_creates_no_audit_log(sales_client, test_lead, session):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={
        "title": "unchanged priority", "priority": "medium"
    })
    task_id = create_res.json()['id']
    session.query(models.AuditLog).delete()
    session.commit()

    sales_client.put(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}", json={"priority": "medium"})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "tasks", models.AuditLog.record_id == task_id
    ).first()
    assert audit is None


def test_update_task_unauthenticated(client, test_lead):
    res = client.put(f"/api/v1/leads/{test_lead.id}/tasks/1", json={"is_completed": True})
    assert res.status_code == 401


# TASKS — DELETE (soft delete, full lead permission required)


def test_delete_task_success(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "to delete"})
    task_id = create_res.json()['id']

    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")
    assert res.status_code == 204


def test_delete_task_soft_deletes_not_removes_row(sales_client, test_lead, session):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "soft delete check"})
    task_id = create_res.json()['id']

    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")
    task = session.query(models.Task).filter(models.Task.id == task_id).first()
    assert task is not None
    assert task.deleted_at is not None
    assert task.deleted_by is not None


def test_delete_task_non_owner_forbidden(sales2_client, test_lead):
    res = sales2_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/1")
    assert res.status_code == 403


def test_delete_task_not_found(sales_client, test_lead):
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/9999")
    assert res.status_code == 404


def test_delete_task_already_deleted_returns_404(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "twice"})
    task_id = create_res.json()['id']

    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")
    assert res.status_code == 404


def test_delete_task_unauthenticated(client, test_lead):
    res = client.delete(f"/api/v1/leads/{test_lead.id}/tasks/1")
    assert res.status_code == 401



# TASKS — RESTORE


def test_restore_task_success(admin_client, sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "restore me"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/restore")
    assert res.status_code == 200
    assert res.json()['deleted_at'] is None


def test_restore_task_non_admin_forbidden(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "restore attempt"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/restore")
    assert res.status_code == 403


def test_restore_task_not_deleted_returns_404(admin_client, sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "not deleted"})
    task_id = create_res.json()['id']

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/restore")
    assert res.status_code == 404


def test_restore_task_visible_again_in_get(admin_client, sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "come back"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")
    admin_client.post(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/restore")

    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/tasks")
    ids = [t['id'] for t in res.json()]
    assert task_id in ids



# TASKS — PERMANENT DELETE


def test_permanent_delete_task_requires_soft_delete_first(admin_client, sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "not soft deleted"})
    task_id = create_res.json()['id']

    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/permanent")
    assert res.status_code == 404


def test_permanent_delete_task_success(admin_client, sales_client, test_lead, session):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "permanent"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/permanent")
    assert res.status_code == 204

    row = session.query(models.Task).filter(models.Task.id == task_id).first()
    assert row is None


def test_permanent_delete_task_non_admin_forbidden(sales_client, test_lead):
    create_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/tasks", json={"title": "protected"})
    task_id = create_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}")

    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/{task_id}/permanent")
    assert res.status_code == 403


def test_permanent_delete_task_not_found(admin_client, test_lead):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tasks/9999/permanent")
    assert res.status_code == 404