from app import models
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta


# GET ALL LEADS

def test_get_all_leads_unauthenticated(client):
    res = client.get("/api/v1/leads/")
    assert res.status_code == 401

def test_get_all_leads_admin_sees_all(admin_client, test_lead, test_lead_admin):
    res = admin_client.get("/api/v1/leads/")
    assert res.status_code == 200
    assert len(res.json()) >= 2

def test_get_all_leads_sales_sees_own_only(sales_client, test_lead, test_lead_admin, test_sales):
    res = sales_client.get("/api/v1/leads/")
    assert res.status_code == 200
    for lead in res.json():
        assert lead['owner_id'] == test_sales.id

def test_get_all_leads_excludes_other_company(admin_client, admin2_client, test_lead,test_company_2, test_admin_company2,
                                                session, test_stage):
    other_lead = models.Lead(
        name="Other Co Lead",
        stage_id=None,
        owner_id=test_admin_company2.id,
        company_id=test_company_2.id,
    )
    session.add(other_lead)
    session.commit()

    res = admin_client.get("/api/v1/leads")
    assert res.status_code == 200
    assert all(lead["company_id"] != test_company_2.id for lead in res.json())

    res = admin_client.get("/api/v1/leads/")
    ids = [l["id"] for l in res.json()]
    assert other_lead.id not in ids

def test_get_all_leads_pagination_limit(admin_client, session, test_admin, test_stage):
    for i in range(5):
        lead = models.Lead(name=f"paginated lead {i}", stage_id=test_stage.id,
                           owner_id=test_admin.id, company_id=test_admin.company_id)
        session.add(lead)
    session.commit()

    res = admin_client.get("/api/v1/leads/?limit=2&skip=0")
    assert res.status_code == 200
    assert len(res.json()) == 2

def test_get_all_leads_pagination_skip(admin_client, session, test_admin, test_stage):
    for i in range(5):
        lead = models.Lead(name=f"skip lead {i}", stage_id=test_stage.id,
                           owner_id=test_admin.id, company_id=test_admin.company_id)
        session.add(lead)
    session.commit()

    res_page1 = admin_client.get("/api/v1/leads/?limit=3&skip=0")
    res_page2 = admin_client.get("/api/v1/leads/?limit=3&skip=3")
    ids_page1 = {l["id"] for l in res_page1.json()}
    ids_page2 = {l["id"] for l in res_page2.json()}
    assert ids_page1.isdisjoint(ids_page2)

def test_get_all_leads_search(admin_client, test_lead):
    res = admin_client.get("/api/v1/leads/?search=Ali")
    assert res.status_code == 200
    assert any("Ali" in lead['name'] for lead in res.json())

def test_get_all_leads_search_no_match(admin_client, test_lead):
    res = admin_client.get("/api/v1/leads/?search=zzzommmat")
    assert res.status_code == 200
    assert res.json() == []

def test_get_all_leads_excludes_soft_deleted(admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = admin_client.get("/api/v1/leads/")
    ids = [l["id"] for l in res.json()]
    assert test_lead.id not in ids

# CREATE LEAD

def test_create_lead_success_sales(sales_client, test_sales, test_stage):
    res = sales_client.post("/api/v1/leads/", json={
        "name": "new lead",
        "email": "newlead@test.com",
        "phone": "03001234567",
        "company": "Test Co",
        "stage_id": test_stage.id
    })
    assert res.status_code == 201
    data = res.json()
    assert data['name'] == "new lead"
    assert data['stage_id'] == test_stage.id
    assert data['owner_id'] == test_sales.id

def test_create_lead_owner_set_automatically(sales_client, test_sales):
    res = sales_client.post("/api/v1/leads/", json={"name": "auto owner lead"})
    assert res.status_code == 201
    assert res.json()['owner_id'] == test_sales.id

def test_create_lead_company_id_set_automatically(sales_client, test_sales):
    res = sales_client.post("/api/v1/leads/", json={"name": "auto company lead"})
    assert res.status_code == 201
    assert res.json()['company_id'] == test_sales.company_id

def test_create_lead_no_stage_auto_assigns_first_stage(sales_client, test_stage):
    # stage_id omitted entirely — should auto-assign the company's lowest-order stage
    res = sales_client.post("/api/v1/leads/", json={"name": "no stage lead"})
    assert res.status_code == 201
    assert res.json()['stage_id'] == test_stage.id

def test_create_lead_explicit_stage_from_other_company_rejected(sales_client, session, test_company_2):
    other_stage = models.PipelineStage(company_id=test_company_2.id, name="Foreign", order=1)
    session.add(other_stage)
    session.commit()
    session.refresh(other_stage)

    res = sales_client.post("/api/v1/leads/", json={"name": "cross stage lead", "stage_id": other_stage.id})
    assert res.status_code == 400

def test_create_lead_unauthorized(client):
    res = client.post("/api/v1/leads/", json={"name": "ghost lead"})
    assert res.status_code == 401

def test_create_lead_missing_name(sales_client):
    res = sales_client.post("/api/v1/leads/", json={})
    assert res.status_code == 422

def test_create_lead_invalid_phone(sales_client):
    res = sales_client.post("/api/v1/leads/", json={"name": "phone lead", "phone": "abc-invalid"})
    assert res.status_code == 422

def test_create_lead_optional_fields_none(sales_client):
    res = sales_client.post("/api/v1/leads/", json={"name": "minimal lead"})
    assert res.status_code == 201
    data = res.json()
    assert data['email'] is None
    assert data['phone'] is None
    assert data['company'] is None

def test_create_lead_by_admin(admin_client, test_admin):
    res = admin_client.post("/api/v1/leads/", json={"name": "admin created lead"})
    assert res.status_code == 201
    assert res.json()['owner_id'] == test_admin.id

def test_create_lead_activity_log(sales_client, session):
    sales_client.post("/api/v1/leads/", json={"name": "log test lead"})
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "Lead Created").first()
    assert log is not None

# GET SINGLE LEAD

def test_get_lead_success_owner(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 200
    assert res.json()['id'] == test_lead.id

def test_get_lead_success_admin(admin_client, test_lead):
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 200

def test_get_lead_success_manager(manager_client, test_lead):
    res = manager_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 200

def test_get_lead_not_found(admin_client):
    res = admin_client.get("/api/v1/leads/99999")
    assert res.status_code == 404

def test_get_lead_sales_cannot_view_others(sales2_client, test_lead):
    res = sales2_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 403

def test_get_lead_unauthenticated(client, test_lead):
    res = client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 401

def test_get_lead_contains_author(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}")
    assert "author" in res.json()

def test_get_lead_from_other_company_returns_404_not_403(admin2_client, test_lead):
    # cross-tenant must look identical to "doesn't exist", never reveal it belongs to someone else
    res = admin2_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 404

def test_get_lead_includes_empty_tags_list(admin_client, test_lead):
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.json()['tags'] == []

def test_get_lead_deleted_at_null_when_not_deleted(admin_client, test_lead):
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.json()['deleted_at'] is None

# UPDATE LEAD

def test_update_lead_admin_success(admin_client, test_lead):
    res = admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "updated lead"})
    assert res.status_code == 200
    assert res.json()['name'] == "updated lead"

def test_update_lead_stage_change(admin_client, test_lead, test_stage_won):
    res = admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"stage_id": test_stage_won.id})
    assert res.status_code == 200
    assert res.json()['stage_id'] == test_stage_won.id

def test_update_lead_sales_owner_allowed(sales_client, test_lead):
    res = sales_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "sales update own lead"})
    assert res.status_code == 200

def test_update_lead_sales_not_owner_forbidden(sales2_client, test_lead):
    res = sales2_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "sales2 update"})
    assert res.status_code == 403

def test_update_lead_manager_no_team_match_forbidden(manager_client, test_lead):
    # test_lead's owner has no team; manager has no team either — should not match
    res = manager_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "manager update"})
    assert res.status_code == 403

def test_update_lead_not_found(admin_client):
    res = admin_client.put("/api/v1/leads/99999", json={"name": "not found"})
    assert res.status_code == 404

def test_update_lead_unauthenticated(client, test_lead):
    res = client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "no auth"})
    assert res.status_code == 401

def test_update_lead_stage_change_creates_activity_log(admin_client, test_lead, test_stage_won, session):
    res = admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"stage_id": test_stage_won.id})
    assert res.status_code == 200
    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Updated and Stage changed").first()
    assert log is not None

def test_update_lead_no_stage_change_logs_generic_update(admin_client, test_lead, session):
    res = admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "Just name change"})
    assert res.status_code == 200
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "Lead Updated").first()
    assert log is not None

def test_update_lead_creates_audit_log_on_field_change(admin_client, test_lead, session):
    old_name = test_lead.name
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "audit test name"})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "leads", models.AuditLog.record_id == test_lead.id,
        models.AuditLog.field_name == "name"
    ).first()
    assert audit is not None
    assert audit.old_value == old_name
    assert audit.new_value == "audit test name"

def test_update_lead_same_value_creates_no_audit_log(admin_client, test_lead, session):
    session.query(models.AuditLog).delete()
    session.commit()

    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": test_lead.name})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "leads", models.AuditLog.record_id == test_lead.id
    ).first()
    assert audit is None

def test_update_lead_from_other_company_returns_404(admin2_client, test_lead):
    res = admin2_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "hijacked"})
    assert res.status_code == 404

# DELETE LEAD (soft delete)

def test_delete_lead_admin_success(admin_client, test_lead):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 204

def test_delete_lead_soft_deletes_not_removes_row(admin_client, test_lead, session):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    lead = session.query(models.Lead).filter(models.Lead.id == test_lead.id).first()
    assert lead is not None  
    assert lead.deleted_at is not None   
    assert lead.deleted_by is not None

def test_delete_lead_hidden_from_normal_get(admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 404

def test_delete_lead_not_found(admin_client):
    res = admin_client.delete("/api/v1/leads/9999")
    assert res.status_code == 404

def test_delete_lead_manager_forbidden(manager_client, test_lead):
    res = manager_client.delete(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 403

def test_delete_lead_sales_forbidden(sales_client, test_lead):
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 403

def test_delete_lead_unauthenticated(client, test_lead):
    res = client.delete(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 401

def test_delete_lead_activity_log(admin_client, test_lead, session):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "Lead Deleted").first()
    assert log is not None

def test_delete_lead_from_other_company_returns_404(admin2_client, test_lead):
    res = admin2_client.delete(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 404

# RESTORE LEAD

def test_restore_lead_success(admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/restore")
    assert res.status_code == 200
    assert res.json()['deleted_at'] is None

def test_restore_lead_visible_again_after_restore(admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    admin_client.post(f"/api/v1/leads/{test_lead.id}/restore")
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}")
    assert res.status_code == 200

def test_restore_lead_not_deleted_returns_404(admin_client, test_lead):
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/restore")
    assert res.status_code == 404

def test_restore_lead_non_admin_forbidden(manager_client, admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = manager_client.post(f"/api/v1/leads/{test_lead.id}/restore")
    assert res.status_code == 403

def test_get_deleted_leads_admin_only(admin_client, sales_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")

    res_admin = admin_client.get("/api/v1/leads/deleted")
    assert res_admin.status_code == 200
    assert any(l["id"] == test_lead.id for l in res_admin.json())

    res_sales = sales_client.get("/api/v1/leads/deleted")
    assert res_sales.status_code == 403


# PERMANENT DELETE


def test_permanent_delete_requires_soft_delete_first(admin_client, test_lead):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/permanent")
    assert res.status_code == 404

def test_permanent_delete_success_after_soft_delete(admin_client, test_lead, session):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/permanent")
    assert res.status_code == 204

    lead = session.query(models.Lead).filter(models.Lead.id == test_lead.id).first()
    assert lead is None  

def test_permanent_delete_non_admin_forbidden(manager_client, admin_client, test_lead):
    admin_client.delete(f"/api/v1/leads/{test_lead.id}")
    res = manager_client.delete(f"/api/v1/leads/{test_lead.id}/permanent")
    assert res.status_code == 403


# ASSIGN LEAD


def test_assign_lead_admin_success(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
    assert res.status_code == 200
    assert res.json()['assigned_to'] == test_sales.id

def test_assign_lead_manager_success(manager_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = manager_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
    assert res.status_code == 200

def test_assign_lead_sales_forbidden(sales_client, test_lead, test_sales):
    res = sales_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
    assert res.status_code == 403

def test_assign_lead_user_not_found(admin_client, test_lead):
    res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": 9999})
    assert res.status_code == 404

def test_assign_lead_cannot_assign_to_admin(admin_client, test_lead, test_admin):
    res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_admin.id})
    assert res.status_code == 400

def test_assign_lead_cannot_assign_to_manager(admin_client, test_lead, test_manager):
    res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_manager.id})
    assert res.status_code == 400

def test_assign_lead_cross_company_user_rejected(admin_client, test_lead, test_admin_company2):
    # attacker-style: pass a valid user id that belongs to a different company entirely
    res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_admin_company2.id})
    assert res.status_code == 404

def test_assign_lead_unauthenticated(client, test_lead, test_sales):
    res = client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
    assert res.status_code == 401

def test_assign_lead_not_found(admin_client, test_sales):
    res = admin_client.patch("/api/v1/leads/9999/assign", json={"assigned_to": test_sales.id})
    assert res.status_code == 404

def test_assign_lead_sends_email(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock) as mock_email:
        admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
        mock_email.assert_called_once()

def test_assign_lead_activity_log(admin_client, test_lead, test_sales, session):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "Lead Assigned").first()
    assert log is not None

def test_assign_lead_creates_notification(admin_client, test_lead, test_sales, session):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})

    notif = session.query(models.Notification).filter(
        models.Notification.user_id == test_sales.id,
        models.Notification.type == models.NotificationType.assignment.value
    ).first()
    assert notif is not None
    assert notif.lead_id == test_lead.id

def test_assign_lead_self_assignment_creates_no_notification(admin_client, test_lead, test_sales, session):
    # assign the lead to test_sales, then have test_sales "reassign" to themselves — should self-guard
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})

    session.query(models.Notification).delete()
    session.commit()
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": test_sales.id})

def test_assign_lead_invalid_zero(admin_client, test_lead):
    res = admin_client.patch(f"/api/v1/leads/{test_lead.id}/assign", json={"assigned_to": 0})
    assert res.status_code == 422


# TAGS ON LEADS (Module 10 integration)


def test_add_tag_to_lead(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="hot", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 200
    assert any(t["id"] == tag.id for t in res.json()["tags"])

def test_add_duplicate_tag_rejected(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="hot", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 400

def test_add_tag_from_other_company_rejected(admin_client, test_lead, session, test_company_2):
    foreign_tag = models.Tag(name="foreign", company_id=test_company_2.id)
    session.add(foreign_tag)
    session.commit()
    session.refresh(foreign_tag)

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{foreign_tag.id}")
    assert res.status_code == 404

def test_remove_tag_from_lead(admin_client, test_lead, session, test_company):
    tag = models.Tag(name="hot", company_id=test_company.id)
    session.add(tag)
    session.commit()
    session.refresh(tag)

    admin_client.post(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/tags/{tag.id}")
    assert res.status_code == 200
    assert not any(t["id"] == tag.id for t in res.json()["tags"])