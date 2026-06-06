from app import models
from unittest.mock import patch, AsyncMock


# Leads Tests

# Get All Leads


def test_get_all_leads_inauthenticated(client):
    res = client.get("/leads")
    assert res.status_code == 401


def test_get_all_leads_admin_sees_all(admin_client, test_lead, test_lead_admin):
    res = admin_client.get("/leads")
    assert res.status_code == 200
    assert len(res.json()) >= 2   


def test_get_all_leads_sales_leads_own(sales_client, test_lead, test_lead_admin, test_sales):
    res = sales_client.get("/leads")
    assert res.status_code == 200
    for lead in res.json():
        assert lead['owner_id'] == test_sales.id

    
def test_get_all_leads_manager_gets_all(manager_client, test_lead, test_lead_admin):
    res = manager_client.get("/leads")
    assert res.status_code == 200
    assert len(res.json()) >= 2   


def test_get_all_leads_pagination_limit(admin_client, session, test_admin):
    for i in range(5):
        lead = models.Lead(
            name=f"paginated lead {i}",
            status= models.LeadStatus.new,
            owner_id=test_admin.id
        )
        session.add(lead)
    session.commit()

    res = admin_client.get("/leads?limit=2&skip=0")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_all_leads_pagination_skip(admin_client, session, test_admin):
    for i in range(5):
        lead = models.Lead(
            name=f"skip lead {i}",
            status= models.LeadStatus.new,
            owner_id=test_admin.id
        )
        session.add(lead)
    session.commit()

    res_page1 = admin_client.get("/leads?limit=3&skip=0")
    res_page2 = admin_client.get("/leads?limit=3&skip=3")
    assert res_page1.status_code == 200
    assert res_page2.status_code == 200
    ids_page1 = {l["id"] for l in res_page1.json()}
    ids_page2 = {l["id"] for l in res_page2.json()}
    assert ids_page1.isdisjoint(ids_page2)


def test_get_all_leads_search(admin_client, test_lead):
    res = admin_client.get("/leads?search=Ali")
    assert res.status_code == 200
    assert any("Ali" in lead['name'] for lead in res.json())


def test_get_lead_no_search(admin_client, test_lead):
    res = admin_client.get("/leads?search=zzzommmat")
    assert res.status_code == 200
    assert res.json() == []


# Create Leads


def test_create_lead_success_sales(sales_client, test_sales):
    res = sales_client.post("leads", json={
        "name": "new lead",
        "email": "newlead@test.com",
        "phone": "03001234567",
        "company": "Test Co",
        "status": "new"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['name'] == "new lead"
    assert data['status'] == "new"
    assert data['owner_id'] == test_sales.id


def test_create_lead_owner_set_automatically(sales_client, test_sales):
    res = sales_client.post("leads", json={
        "name": "auto owner lead",
        "status": "new"
    })
    assert res.status_code == 201
    assert res.json()['owner_id'] == test_sales.id


def test_create_lead_unauthorized(client):
    res = client.post("leads", json={
        "name": "ghost lead",
        "status": "new"
    })
    assert res.status_code == 401


def test_create_lead_missing_name(sales_client):
    res = sales_client.post("leads", json={
        "status": "new"
    })
    assert res.status_code == 422


def test_create_lead_invalid_phone(sales_client):
    res = sales_client.post("leads", json={
        "name": "phone lead",
        "status": "new",
        "phone": "abc-invalid"
    })
    assert res.status_code == 422


def test_create_lead_all_statuses(sales_client):
    for status_val in ["new", "contacted", "qualified", "won", "lost"]:
        res = sales_client.post("leads", json={
            "name": f"lead {status_val}",
            "status": status_val
        })
    assert res.status_code == 201


def test_create_lead_optional_fields_none(sales_client):
    res = sales_client.post("leads", json={
        "name": "minimal lead",
        "status": "new"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['email'] is None
    assert data['phone'] is None
    assert data['company'] is None


def test_create_lead_by_admin(admin_client, test_admin):
    res = admin_client.post("leads", json={
        "name": "admin created lead",
        "status": "new"
    })
    assert res.status_code == 201
    assert res.json()['owner_id'] == test_admin.id


def test_create_lead_activity_log(sales_client, session):
    sales_client.post("leads", json={
        "name": "log test lead",
        "status": "new"
    })
    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Created").first()
    assert log is not None


# Get Single Lead


def test_get_lead_success_owner(sales_client, test_lead):
    res = sales_client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 200
    assert res.json()['id'] == test_lead.id


def test_get_lead_success_admin(admin_client, test_lead):
    res = admin_client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 200


def test_get_lead_success_manager(manager_client, test_lead):
    res = manager_client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 200


def test_get_lead_admin_lead_not_found(admin_client):
    res = admin_client.get("/leads/99999")
    assert res.status_code == 404


def test_get_lead_sales_cannot_view_others(sales2_client, test_lead):
    res = sales2_client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 403


def test_get_lead_unauthenticated(client, test_lead):
    res = client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 401


def test_get_lead_contain_author(sales_client, test_lead):
    res = sales_client.get(f"/leads/{test_lead.id}")
    assert res.status_code == 200
    assert "author" in res.json()


# Update Lead Tests


def test_update_lead_admin_test(admin_client, test_lead):
    res = admin_client.put(f"/leads/{test_lead.id}", json={
        "name": "updated lead",
        "status": "contacted"
    })
    assert res.status_code == 200
    data = res.json()
    assert data['name'] == "updated lead"
    assert data['status'] == "contacted"


def test_update_lead_sales_forbidden(sales_client, test_lead):
    res = sales_client.put(f"/leads/{test_lead.id}", json={
        "name": "sales update"
    })
    assert res.status_code == 403


def test_update_lead_manager_forbidden(manager_client, test_lead):
    res = manager_client.put(f"/leads/{test_lead.id}", json={
        "name": "manager update"
    })
    assert res.status_code == 403


def test_update_lead_admin_lead_not_found(admin_client, test_lead):
    res = admin_client.put("/leads/99999", json={
        "name": "not found"
    })
    assert res.status_code == 404


def test_update_lead_unauthenticated(client, test_lead):
    res = client.put(f"/leads/{test_lead.id}", json={
        "name": "no auth"
    })
    assert res.status_code == 401


def test_update_lead_status_log_change_correctly(admin_client, test_lead, session):
    res = admin_client.put(f"/leads/{test_lead.id}", json={
        "status": "won"
    })
    assert res.status_code == 200

    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Updated and Status changed").first()
    assert log is not None


def test_update_lead_no_status_log_change_correctly(admin_client, test_lead, session):
    res = admin_client.put(f"/leads/{test_lead.id}", json={
        "name": "Just name change"
    })
    assert res.status_code == 200

    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Updated").first()
    assert log is not None


# Delete Lead


def test_delete_lead_admin_success(admin_client, test_lead):
    res = admin_client.delete(f"/leads/{test_lead.id}")
    assert res.status_code == 204


def test_delete_lead_actually_deleted(admin_client, test_lead, session):
    res = admin_client.delete(f"/leads/{test_lead.id}")
    lead = session.query(models.Lead).filter(
        models.Lead.id == test_lead.id).first()
    assert lead is None


def test_delete_lead_admin_not_found(admin_client):
    res = admin_client.delete("/leads/9999")
    assert res.status_code == 404


def test_delete_lead_manager_forbidden(manager_client, test_lead):
    res = manager_client.delete(f"/leads/{test_lead.id}")
    assert res.status_code == 403


def test_delete_lead_sales_forbidden(sales_client, test_lead):
    res = sales_client.delete(f"/leads/{test_lead.id}")
    assert res.status_code == 403


def test_delete_lead_unauthenticated(client, test_lead):
    res = client.put(f"/leads/{test_lead.id}")
    assert res.status_code == 401


def test_delete_lead_activity_log(admin_client, test_lead, session):
    res = admin_client.delete(f"/leads/{test_lead.id}")

    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Deleted").first()
    assert log is not None


# Assign Lead Tests


def test_asssign_lead_admin_success(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
    assert res.status_code == 200
    assert res.json()['assigned_to'] == test_sales.id


def test_asssign_lead_manager_success(manager_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = manager_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
    assert res.status_code == 200
    assert res.json()['assigned_to'] == test_sales.id


def test_asssign_lead_sales_forbidden(sales_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = sales_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
    assert res.status_code == 403


def test_asssign_lead_admin_not_found(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": 9999
        })
    assert res.status_code == 404


def test_asssign_lead_admin_cannot_assign_to_admin(admin_client, test_lead, test_admin):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_admin.id
        })
    assert res.status_code == 400


def test_asssign_lead_admin_cannot_assign_to_manager(admin_client, test_lead, test_manager):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_manager.id
        })
    assert res.status_code == 400


def test_asssign_lead_admin_unauthorized(client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
    assert res.status_code == 401


def test_asssign_lead_not_found(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch("/leads/9999/assign", json={
            "assigned_to": test_sales.id
        })
    assert res.status_code == 404


def test_asssign_lead_sends_email(admin_client, test_lead, test_sales):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock) as mock_email:
        admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
        mock_email.assert_called_once()


def test_assign_lead_activity_log(admin_client, test_lead, test_sales, session):
    with patch("app.routers.lead.send_lead_assigned_email", new_callable=AsyncMock):
        res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
            "assigned_to": test_sales.id
        })
    
    assert res.status_code == 200  

    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "Lead Assigned").first()
    assert log is not None


def test_asssign_lead_invalid_assign_to_zero(admin_client, test_lead):
    res = admin_client.patch(f"/leads/{test_lead.id}/assign", json={
        "assigned_to": 0
    })
    assert res.status_code == 422