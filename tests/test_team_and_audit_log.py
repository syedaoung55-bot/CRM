from app import models


# CREATE TEAM

def test_create_team_admin_success(admin_client, test_manager):
    res = admin_client.post("/api/v1/teams/", json={"name": "Sales Team A", "manager_id": test_manager.id})
    assert res.status_code == 201
    assert res.json()['manager_id'] == test_manager.id


def test_create_team_no_manager(admin_client):
    res = admin_client.post("/api/v1/teams/", json={"name": "No Manager Yet"})
    assert res.status_code == 201
    assert res.json()['manager_id'] is None


def test_create_team_manager_forbidden(manager_client):
    res = manager_client.post("/api/v1/teams/", json={"name": "Shouldn't work"})
    assert res.status_code == 403


def test_create_team_sales_forbidden(sales_client):
    res = sales_client.post("/api/v1/teams/", json={"name": "Shouldn't work either"})
    assert res.status_code == 403


def test_create_team_unauthenticated(client):
    res = client.post("/api/v1/teams/", json={"name": "no auth"})
    assert res.status_code == 401


def test_create_team_missing_name(admin_client):
    res = admin_client.post("/api/v1/teams/", json={})
    assert res.status_code == 422


def test_create_team_manager_id_must_have_manager_role(admin_client, test_sales):
    res = admin_client.post("/api/v1/teams/", json={"name": "Bad Team", "manager_id": test_sales.id})
    assert res.status_code == 400


def test_create_team_manager_id_not_found(admin_client):
    res = admin_client.post("/api/v1/teams/", json={"name": "Ghost Manager", "manager_id": 9999})
    assert res.status_code == 404


def test_create_team_manager_id_cross_company_rejected(admin_client, session, test_company_2):
    other_manager = models.User(email="othermgr@test.com", password="x", full_name="Other Mgr",
                                role=models.UserRole.manager, company_id=test_company_2.id)
    session.add(other_manager)
    session.commit()
    session.refresh(other_manager)

    res = admin_client.post("/api/v1/teams/", json={"name": "Cross Team", "manager_id": other_manager.id})
    assert res.status_code == 404


def test_create_team_company_id_set_automatically(admin_client, test_company):
    res = admin_client.post("/api/v1/teams/", json={"name": "Auto Company"})
    assert res.json()['company_id'] == test_company.id


# GET ALL TEAMS 

def test_get_all_teams_admin(admin_client, test_team):
    res = admin_client.get("/api/v1/teams/")
    assert res.status_code == 200
    assert any(t["id"] == test_team.id for t in res.json())


def test_get_all_teams_sales_allowed(sales_client, test_team):
    res = sales_client.get("/api/v1/teams/")
    assert res.status_code == 200


def test_get_all_teams_manager_allowed(manager_client, test_team):
    res = manager_client.get("/api/v1/teams/")
    assert res.status_code == 200


def test_get_all_teams_excludes_other_company(admin_client, session, test_company_2):
    other_team = models.Team(name="Other Co Team", company_id=test_company_2.id)
    session.add(other_team)
    session.commit()

    res = admin_client.get("/api/v1/teams/")
    ids = [t["id"] for t in res.json()]
    assert other_team.id not in ids


def test_get_all_teams_unauthenticated(client):
    res = client.get("/api/v1/teams/")
    assert res.status_code == 401


# GET SINGLE TEAM 

def test_get_team_by_id(admin_client, test_team):
    res = admin_client.get(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 200
    assert res.json()['id'] == test_team.id


def test_get_team_sales_allowed(sales_client, test_team):
    res = sales_client.get(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 200


def test_get_team_not_found(admin_client):
    res = admin_client.get("/api/v1/teams/9999")
    assert res.status_code == 404


def test_get_team_from_other_company_returns_404(admin2_client, test_team):
    res = admin2_client.get(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 404


def test_get_team_unauthenticated(client, test_team):
    res = client.get(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 401


# ADD MEMBER

def test_add_member_success(admin_client, test_team, test_sales):
    res = admin_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales.id}")
    assert res.status_code == 200
    assert res.json()['team_id'] == test_team.id


def test_add_member_non_admin_forbidden(manager_client, test_team, test_sales):
    res = manager_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales.id}")
    assert res.status_code == 403


def test_add_member_sales_forbidden(sales_client, test_team, test_sales2):
    res = sales_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales2.id}")
    assert res.status_code == 403


def test_add_member_team_not_found(admin_client, test_sales):
    res = admin_client.patch(f"/api/v1/teams/9999/members/{test_sales.id}")
    assert res.status_code == 404


def test_add_member_user_not_found(admin_client, test_team):
    res = admin_client.patch(f"/api/v1/teams/{test_team.id}/members/9999")
    assert res.status_code == 404


def test_add_member_cross_company_user_rejected(admin_client, test_team, test_admin_company2):
    res = admin_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_admin_company2.id}")
    assert res.status_code == 404


def test_add_member_team_from_other_company_rejected(admin_client, session, test_company_2, test_sales):
    other_team = models.Team(name="Foreign Team", company_id=test_company_2.id)
    session.add(other_team)
    session.commit()
    session.refresh(other_team)

    res = admin_client.patch(f"/api/v1/teams/{other_team.id}/members/{test_sales.id}")
    assert res.status_code == 404


def test_add_member_unauthenticated(client, test_team, test_sales):
    res = client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales.id}")
    assert res.status_code == 401


def test_add_member_admin_role_can_be_added_too(admin_client, test_team, test_admin):
    # no role restriction on who can BE a member — an admin can be assigned team_id too
    res = admin_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_admin.id}")
    assert res.status_code == 200


def test_add_member_moves_between_teams(admin_client, test_company, test_sales, session):
    team1 = models.Team(name="Team One", company_id=test_company.id)
    team2 = models.Team(name="Team Two", company_id=test_company.id)
    session.add_all([team1, team2])
    session.commit()
    session.refresh(team1)
    session.refresh(team2)

    admin_client.patch(f"/api/v1/teams/{team1.id}/members/{test_sales.id}")
    res = admin_client.patch(f"/api/v1/teams/{team2.id}/members/{test_sales.id}")
    assert res.status_code == 200
    assert res.json()['team_id'] == team2.id   # reassigned, not left on team1 too


# UPDATE TEAM

def test_update_team_name(admin_client, test_team):
    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "Renamed Team"})
    assert res.status_code == 200
    assert res.json()['name'] == "Renamed Team"


def test_update_team_manager_to_valid_manager(admin_client, test_team, test_company, session):
    new_manager = models.User(email="newmgr@test.com", password="x", full_name="New Mgr",
                              role=models.UserRole.manager, company_id=test_company.id)
    session.add(new_manager)
    session.commit()
    session.refresh(new_manager)

    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"manager_id": new_manager.id})
    assert res.status_code == 200
    assert res.json()['manager_id'] == new_manager.id


def test_update_team_manager_id_no_role_validation_gap(admin_client, test_team, test_sales):
    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"manager_id": test_sales.id})
    assert res.status_code == 400

def test_update_team_manager_id_no_existence_check_gap(admin_client, test_team):
    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"manager_id": 999999})
    assert res.status_code == 404


def test_update_team_manager_id_cross_company_no_check_gap(admin_client, test_team, test_admin_company2):
    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"manager_id": test_admin_company2.id})
    assert res.status_code == 404


def test_update_team_non_admin_forbidden(manager_client, test_team):
    res = manager_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "hijack"})
    assert res.status_code == 403


def test_update_team_not_found(admin_client):
    res = admin_client.put("/api/v1/teams/9999", json={"name": "ghost"})
    assert res.status_code == 404


def test_update_team_from_other_company_returns_404(admin2_client, test_team):
    res = admin2_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "hijack cross tenant"})
    assert res.status_code == 404


def test_update_team_partial_update_preserves_other_field(admin_client, test_team):
    original_manager_id = test_team.manager_id
    res = admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "only name changed"})
    assert res.json()['manager_id'] == original_manager_id


def test_update_team_creates_audit_log_on_name_change(admin_client, test_team, session):
    old_name = test_team.name
    admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "audited name"})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "teams", models.AuditLog.record_id == test_team.id,
        models.AuditLog.field_name == "name"
    ).first()
    assert audit is not None
    assert audit.old_value == old_name
    assert audit.new_value == "audited name"


def test_update_team_no_audit_log_when_value_unchanged(admin_client, test_team, session):
    session.query(models.AuditLog).delete()
    session.commit()

    admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": test_team.name})

    audit = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "teams", models.AuditLog.record_id == test_team.id
    ).first()
    assert audit is None


def test_update_team_unauthenticated(client, test_team):
    res = client.put(f"/api/v1/teams/{test_team.id}", json={"name": "no auth"})
    assert res.status_code == 401


# DELETE TEAM

def test_delete_team_admin_success(admin_client, test_team):
    res = admin_client.delete(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 204


def test_delete_team_actually_removed(admin_client, session, test_company):
    team = models.Team(name="to be deleted", company_id=test_company.id)
    session.add(team)
    session.commit()
    session.refresh(team)
    team_id = team.id

    admin_client.delete(f"/api/v1/teams/{team_id}")
    row = session.query(models.Team).filter(models.Team.id == team_id).first()
    assert row is None   # hard delete — Team has no deleted_at


def test_delete_team_non_admin_forbidden(manager_client, test_team):
    res = manager_client.delete(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 403


def test_delete_team_not_found(admin_client):
    res = admin_client.delete("/api/v1/teams/9999")
    assert res.status_code == 404


def test_delete_team_from_other_company_returns_404(admin2_client, test_team):
    res = admin2_client.delete(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 404


def test_delete_team_unauthenticated(client, test_team):
    res = client.delete(f"/api/v1/teams/{test_team.id}")
    assert res.status_code == 401


def test_delete_team_member_orphaned_not_cascaded(admin_client, test_team, test_sales, session):
    admin_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales.id}")
    admin_client.delete(f"/api/v1/teams/{test_team.id}")

    session.refresh(test_sales)
    assert test_sales.team_id is None
    user_row = session.query(models.User).filter(models.User.id == test_sales.id).first()
    assert user_row is not None   # user itself untouched


# INTEGRATION: team membership actually changes lead permission

def test_manager_can_act_on_teammates_lead(admin_client, manager_client, test_team, test_sales, test_stage, session, test_company):
    admin_client.patch(f"/api/v1/teams/{test_team.id}/members/{test_sales.id}")

    lead = models.Lead(name="Team Lead", stage_id=test_stage.id, owner_id=test_sales.id,
                       assigned_to=test_sales.id, company_id=test_company.id)
    session.add(lead)
    session.commit()
    session.refresh(lead)

    res = manager_client.put(f"/api/v1/leads/{lead.id}", json={"name": "manager updated teammate lead"})
    assert res.status_code == 200


def test_manager_cannot_act_on_non_teammates_lead(manager_client, test_lead):
    res = manager_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "should fail"})
    assert res.status_code == 403


# AUDIT LOGS

def test_get_audit_logs_admin_only(admin_client, sales_client, test_lead):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "trigger a log"})

    res_admin = admin_client.get("/api/v1/audit-logs/")
    assert res_admin.status_code == 200

    res_sales = sales_client.get("/api/v1/audit-logs/")
    assert res_sales.status_code == 403


def test_get_audit_logs_manager_forbidden(manager_client):
    res = manager_client.get("/api/v1/audit-logs/")
    assert res.status_code == 403


def test_get_audit_logs_unauthenticated(client):
    res = client.get("/api/v1/audit-logs/")
    assert res.status_code == 401


def test_get_audit_logs_filter_by_table_name(admin_client, test_lead, test_team):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "lead change"})
    admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "team change"})

    res = admin_client.get("/api/v1/audit-logs/?table_name=leads")
    assert res.status_code == 200
    assert all(a['table_name'] == "leads" for a in res.json())


def test_get_audit_logs_filter_by_record_id(admin_client, test_lead, test_lead_admin):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "lead A change"})
    admin_client.put(f"/api/v1/leads/{test_lead_admin.id}", json={"name": "lead B change"})

    res = admin_client.get(f"/api/v1/audit-logs/?table_name=leads&record_id={test_lead.id}")
    assert res.status_code == 200
    assert all(a['record_id'] == test_lead.id for a in res.json())


def test_get_audit_logs_no_filters_returns_all_company_logs(admin_client, test_lead, test_team):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "one change"})
    admin_client.put(f"/api/v1/teams/{test_team.id}", json={"name": "another change"})

    res = admin_client.get("/api/v1/audit-logs/")
    table_names = {a['table_name'] for a in res.json()}
    assert "leads" in table_names
    assert "teams" in table_names


def test_get_audit_logs_excludes_other_company(admin_client, admin2_client, test_lead):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "company 1 only"})

    res = admin2_client.get("/api/v1/audit-logs/")
    assert res.json() == []


def test_get_audit_logs_ordered_newest_first(admin_client, test_lead, session):
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "first change"})
    admin_client.put(f"/api/v1/leads/{test_lead.id}", json={"name": "second change"})

    res = admin_client.get("/api/v1/audit-logs/")
    logs = res.json()
    if len(logs) >= 2:
        assert logs[0]['created_at'] >= logs[1]['created_at']


def test_get_audit_logs_empty_when_nothing_changed(admin_client):
    res = admin_client.get("/api/v1/audit-logs/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)