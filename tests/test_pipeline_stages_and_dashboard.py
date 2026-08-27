from app import models
from datetime import datetime, timezone, timedelta


# CREATE STAGE


def test_create_stage_admin_success(admin_client, test_company):
    res = admin_client.post("/api/v1/pipeline-stages", json={
        "name": "Negotiation", "order": 3, "is_won": False, "is_lost": False
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Negotiation"
    assert data["company_id"] == test_company.id


def test_create_stage_defaults_is_won_is_lost_false(admin_client):
    res = admin_client.post("/api/v1/pipeline-stages", json={"name": "New Stage", "order": 1})
    assert res.status_code == 201
    data = res.json()
    assert data["is_won"] is False
    assert data["is_lost"] is False


def test_create_stage_manager_forbidden(manager_client):
    res = manager_client.post("/api/v1/pipeline-stages", json={"name": "X", "order": 1})
    assert res.status_code == 403


def test_create_stage_sales_forbidden(sales_client):
    res = sales_client.post("/api/v1/pipeline-stages", json={"name": "X", "order": 1})
    assert res.status_code == 403


def test_create_stage_unauthenticated(client):
    res = client.post("/api/v1/pipeline-stages", json={"name": "X", "order": 1})
    assert res.status_code == 401


def test_create_stage_missing_name(admin_client):
    res = admin_client.post("/api/v1/pipeline-stages", json={"order": 1})
    assert res.status_code == 422


def test_create_stage_missing_order(admin_client):
    res = admin_client.post("/api/v1/pipeline-stages", json={"name": "No order"})
    assert res.status_code == 422



# GET ALL STAGES

def test_get_all_stages_admin_success(admin_client, test_stage, test_stage_won):
    res = admin_client.get("/api/v1/pipeline-stages")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_get_all_stages_manager_forbidden(manager_client, test_stage):
    res = manager_client.get("/api/v1/pipeline-stages")
    assert res.status_code == 403


def test_get_all_stages_sales_forbidden(sales_client, test_stage):
    res = sales_client.get("/api/v1/pipeline-stages")
    assert res.status_code == 403


def test_get_all_stages_unauthenticated(client):
    res = client.get("/api/v1/pipeline-stages")
    assert res.status_code == 401


def test_get_all_stages_ordered_by_order(admin_client, test_stage, test_stage_won):
    res = admin_client.get("/api/v1/pipeline-stages")
    names = [s["name"] for s in res.json()]
    assert names == [test_stage.name, test_stage_won.name]


def test_get_all_stages_excludes_other_company(admin_client, test_stage, test_company_2, session):
    other_stage = models.PipelineStage(company_id=test_company_2.id, name="Other Co Stage", order=1)
    session.add(other_stage)
    session.commit()

    res = admin_client.get("/api/v1/pipeline-stages")
    names = [s["name"] for s in res.json()]
    assert "Other Co Stage" not in names


def test_get_all_stages_empty(admin_client):
    res = admin_client.get("/api/v1/pipeline-stages")
    assert res.status_code == 200
    assert res.json() == []


# UPDATE STAGE


def test_update_stage_admin_success(admin_client, test_stage):
    res = admin_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "Renamed"})
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


def test_update_stage_order_change(admin_client, test_stage):
    res = admin_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"order": 5})
    assert res.status_code == 200
    assert res.json()["order"] == 5


def test_update_stage_is_won_flag(admin_client, test_stage):
    res = admin_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"is_won": True})
    assert res.status_code == 200
    assert res.json()["is_won"] is True


def test_update_stage_not_found(admin_client):
    res = admin_client.put("/api/v1/pipeline-stages/9999", json={"name": "Ghost"})
    assert res.status_code == 404


def test_update_stage_manager_forbidden(manager_client, test_stage):
    res = manager_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "Hacked"})
    assert res.status_code == 403


def test_update_stage_sales_forbidden(sales_client, test_stage):
    res = sales_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "Hacked"})
    assert res.status_code == 403


def test_update_stage_unauthenticated(client, test_stage):
    res = client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "No auth"})
    assert res.status_code == 401


def test_update_stage_cross_company_not_found(admin2_client, test_stage):
    res = admin2_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "Cross tenant"})
    assert res.status_code == 404


def test_update_stage_creates_audit_log(admin_client, test_stage, session):
    admin_client.put(f"/api/v1/pipeline-stages/{test_stage.id}", json={"name": "Audited Name"})
    log = session.query(models.AuditLog).filter(
        models.AuditLog.table_name == "Stages", models.AuditLog.field_name == "name"
    ).first()
    assert log is not None


# DELETE STAGE


def test_delete_stage_admin_success(admin_client, test_stage_won):
    res = admin_client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    assert res.status_code == 204


def test_delete_stage_with_leads_rejected(admin_client, test_stage, test_lead):
    res = admin_client.delete(f"/api/v1/pipeline-stages/{test_stage.id}")
    assert res.status_code == 400


def test_delete_stage_not_found(admin_client):
    res = admin_client.delete("/api/v1/pipeline-stages/9999")
    assert res.status_code == 404


def test_delete_stage_manager_forbidden(manager_client, test_stage_won):
    res = manager_client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    assert res.status_code == 403


def test_delete_stage_sales_forbidden(sales_client, test_stage_won):
    res = sales_client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    assert res.status_code == 403


def test_delete_stage_unauthenticated(client, test_stage_won):
    res = client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    assert res.status_code == 401


def test_delete_stage_cross_company_not_found(admin2_client, test_stage_won):
    res = admin2_client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    assert res.status_code == 404


def test_delete_stage_actually_removed(admin_client, test_stage_won, session):
    admin_client.delete(f"/api/v1/pipeline-stages/{test_stage_won.id}")
    stage = session.query(models.PipelineStage).filter(models.PipelineStage.id == test_stage_won.id).first()
    assert stage is None

# DASHBOARD

# ACCESS CONTROL

def test_dashboard_summary_unauthenticated(client):
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 401


def test_dashboard_summary_success(admin_client):
    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_leads" in data
    assert "open_leads" in data
    assert "won_leads" in data
    assert "lost_leads" in data
    assert "leads_by_stage" in data
    assert "tasks" in data
    assert "team_performance" in data


def test_dashboard_summary_accessible_by_sales(sales_client):
    res = sales_client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200


def test_dashboard_summary_accessible_by_manager(manager_client):
    res = manager_client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200


# LEAD COUNTS


def test_dashboard_empty_company_returns_zeros(admin_client):
    res = admin_client.get("/api/v1/dashboard/summary")
    data = res.json()
    assert data["total_leads"] == 0
    assert data["open_leads"] == 0
    assert data["won_leads"] == 0
    assert data["lost_leads"] == 0


def test_dashboard_total_leads_count(admin_client, test_lead, test_lead_admin):
    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["total_leads"] == 2


def test_dashboard_excludes_soft_deleted_leads(admin_client, test_lead, session):
    test_lead.deleted_at = datetime.now(timezone.utc)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["total_leads"] == 0


def test_dashboard_won_leads_count(admin_client, test_lead, test_stage_won, session):
    test_lead.stage_id = test_stage_won.id
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    data = res.json()
    assert data["won_leads"] == 1
    assert data["open_leads"] == 0


def test_dashboard_lost_leads_count(admin_client, test_lead, test_company, session):
    lost_stage = models.PipelineStage(company_id=test_company.id, name="Lost", order=3, is_won=False, is_lost=True)
    session.add(lost_stage)
    session.commit()
    session.refresh(lost_stage)

    test_lead.stage_id = lost_stage.id
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    data = res.json()
    assert data["lost_leads"] == 1
    assert data["open_leads"] == 0


def test_dashboard_open_leads_excludes_won_and_lost(admin_client, test_lead, test_lead_admin, test_stage_won, session):
    test_lead.stage_id = test_stage_won.id
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    data = res.json()
    assert data["total_leads"] == 2
    assert data["won_leads"] == 1
    assert data["open_leads"] == 1


def test_dashboard_excludes_other_company_leads(admin_client, test_lead, test_company_2, test_admin_company2, session):
    other_stage = models.PipelineStage(company_id=test_company_2.id, name="New", order=1, is_won=False, is_lost=False)
    session.add(other_stage)
    session.commit()
    session.refresh(other_stage)

    other_lead = models.Lead(name="Other Co Lead", stage_id=other_stage.id,
                             owner_id=test_admin_company2.id, company_id=test_company_2.id)
    session.add(other_lead)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["total_leads"] == 1



# LEADS BY STAGE


def test_dashboard_leads_by_stage_counts(admin_client, test_lead, test_stage):
    res = admin_client.get("/api/v1/dashboard/summary")
    stages = {s["stage_name"]: s["count"] for s in res.json()["leads_by_stage"]}
    assert stages[test_stage.name] == 1


def test_dashboard_leads_by_stage_includes_empty_stages(admin_client, test_stage_won):
    res = admin_client.get("/api/v1/dashboard/summary")
    stages = {s["stage_name"]: s["count"] for s in res.json()["leads_by_stage"]}
    assert stages[test_stage_won.name] == 0


def test_dashboard_leads_by_stage_ordered_by_stage_order(admin_client, test_stage, test_stage_won):
    res = admin_client.get("/api/v1/dashboard/summary")
    names = [s["stage_name"] for s in res.json()["leads_by_stage"]]
    assert names.index(test_stage.name) < names.index(test_stage_won.name)



# TASKS SUMMARY


def test_dashboard_tasks_total_count(admin_client, test_lead, session):
    task = models.Task(title="Follow up", lead_id=test_lead.id, priority=models.TaskPriority.medium)
    session.add(task)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["total"] == 1


def test_dashboard_tasks_completed_count(admin_client, test_lead, session):
    task = models.Task(title="Done task", lead_id=test_lead.id, priority=models.TaskPriority.medium, is_completed=True)
    session.add(task)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["completed"] == 1


def test_dashboard_tasks_overdue_count(admin_client, test_lead, session):
    task = models.Task(title="Overdue", lead_id=test_lead.id, priority=models.TaskPriority.medium,
                       due_date=datetime.now(timezone.utc) - timedelta(days=1), is_completed=False)
    session.add(task)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["overdue"] == 1


def test_dashboard_tasks_not_overdue_if_completed(admin_client, test_lead, session):
    task = models.Task(title="Completed but past due", lead_id=test_lead.id, priority=models.TaskPriority.medium,
                       due_date=datetime.now(timezone.utc) - timedelta(days=1), is_completed=True)
    session.add(task)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["overdue"] == 0


def test_dashboard_tasks_excludes_deleted(admin_client, test_lead, session):
    task = models.Task(title="Deleted task", lead_id=test_lead.id, priority=models.TaskPriority.medium,
                       deleted_at=datetime.now(timezone.utc))
    session.add(task)
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["total"] == 0


def test_dashboard_tasks_excludes_leads_soft_deleted(admin_client, test_lead, session):
    test_lead.deleted_at = datetime.now(timezone.utc)
    session.add(models.Task(title="Orphaned task", lead_id=test_lead.id, priority=models.TaskPriority.medium))
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["tasks"]["total"] == 0


# TEAM PERFORMANCE


def test_dashboard_team_performance_included(admin_client, test_team):
    res = admin_client.get("/api/v1/dashboard/summary")
    team_names = [t["team_name"] for t in res.json()["team_performance"]]
    assert test_team.name in team_names


def test_dashboard_team_performance_counts_assigned_leads(admin_client, test_team, test_sales, test_lead, session):
    test_sales.team_id = test_team.id
    test_lead.assigned_to = test_sales.id
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    team = next(t for t in res.json()["team_performance"] if t["team_name"] == test_team.name)
    assert team["total_leads"] == 1


def test_dashboard_team_performance_counts_won_leads(admin_client, test_team, test_sales, test_lead, test_stage_won, session):
    test_sales.team_id = test_team.id
    test_lead.assigned_to = test_sales.id
    test_lead.stage_id = test_stage_won.id
    session.commit()

    res = admin_client.get("/api/v1/dashboard/summary")
    team = next(t for t in res.json()["team_performance"] if t["team_name"] == test_team.name)
    assert team["won_leads"] == 1


def test_dashboard_no_teams_returns_empty_performance_list(admin_client):
    res = admin_client.get("/api/v1/dashboard/summary")
    assert res.json()["team_performance"] == []