from sqlalchemy import create_engine
from app.config import settings
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import pytest
from app.main import app
from sqlalchemy import text
from app.utils.utils import hash
from unittest.mock import patch, AsyncMock
from app import models
from app.database import get_db, Base

SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}_test'
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def session():
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    db = TestingSessionlocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            pass
    with patch("app.utils.email.send_welcome_email", new_callable=AsyncMock), \
         patch("app.utils.email.send_lead_assigned_email", new_callable=AsyncMock), \
         patch("app.utils.email.send_invite_email", new_callable=AsyncMock), \
         patch("app.utils.email.send_password_reset_email", new_callable=AsyncMock), \
         patch("app.utils.email.send_verification_email", new_callable=AsyncMock):
        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)

    app.dependency_overrides.clear()

@pytest.fixture()
def test_company(session):
    company = models.Company(name="Test Company")
    session.add(company)
    session.commit()
    session.refresh(company)
    return company

@pytest.fixture()
def test_company_2(session):
    company = models.Company(name="Other Company")
    session.add(company)
    session.commit()
    session.refresh(company)
    return company

@pytest.fixture()
def test_admin(session, test_company):
    user = models.User(
        email="admin@test.com", password=hash("admin123"), full_name="Test Admin",
        role=models.UserRole.admin, is_active=True, company_id=test_company.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture()
def test_manager(session, test_company):
    user = models.User(
        email="manager@test.com", password=hash("manager123"), full_name="Test Manager",
        role=models.UserRole.manager, is_active=True, company_id=test_company.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture()
def test_sales(session, test_company):
    user = models.User(
        email="sales@test.com", password=hash("sales123"), full_name="Test Sales",
        role=models.UserRole.sales, is_active=True, company_id=test_company.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture()
def test_sales2(session, test_company):
    user = models.User(
        email="sales2@test.com", password=hash("sales123"), full_name="Test Sales Two",
        role=models.UserRole.sales, is_active=True, company_id=test_company.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture()
def test_admin_company2(session, test_company_2):
    user = models.User(
        email="admin2@test.com", password=hash("admin123"), full_name="Other Admin",
        role=models.UserRole.admin, is_active=True, company_id=test_company_2.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@pytest.fixture()
def admin_token(test_admin, client):
    res = client.post("/api/v1/auth/login", data={"username": "admin@test.com", "password": "admin123"})
    return res.json()["access_token"]

@pytest.fixture()
def admin_refresh_token(test_admin, client):
    res = client.post("/api/v1/auth/login", data={"username": "admin@test.com", "password": "admin123"})
    return res.json()["refresh_token"]

@pytest.fixture()
def manager_token(test_manager, client):
    res = client.post("/api/v1/auth/login", data={"username": "manager@test.com", "password": "manager123"})
    return res.json()["access_token"]

@pytest.fixture()
def sales_token(test_sales, client):
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    return res.json()["access_token"]

@pytest.fixture()
def sales_refresh_token(test_sales, client):
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    return res.json()["refresh_token"]

@pytest.fixture()
def sales2_token(test_sales2, client):
    res = client.post("/api/v1/auth/login", data={"username": "sales2@test.com", "password": "sales123"})
    return res.json()["access_token"]

@pytest.fixture()
def admin2_token(test_admin_company2, client):
    res = client.post("/api/v1/auth/login", data={"username": "admin2@test.com", "password": "admin123"})
    return res.json()["access_token"]

@pytest.fixture()
def admin_client(client, admin_token):
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {admin_token}"})
    return c

@pytest.fixture()
def manager_client(client, manager_token):
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {manager_token}"})
    return c

@pytest.fixture()
def sales_client(client, sales_token):
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {sales_token}"})
    return c

@pytest.fixture()
def sales2_client(client, sales2_token):
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {sales2_token}"})
    return c

@pytest.fixture()
def admin2_client(client, admin2_token):
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {admin2_token}"})
    return c

@pytest.fixture()
def test_stage(session, test_company):
    stage = models.PipelineStage(company_id=test_company.id, name="New", order=1, is_won=False, is_lost=False)
    session.add(stage)
    session.commit()
    session.refresh(stage)
    return stage

@pytest.fixture()
def test_stage_won(session, test_company):
    stage = models.PipelineStage(company_id=test_company.id, name="Won", order=2, is_won=True, is_lost=False)
    session.add(stage)
    session.commit()
    session.refresh(stage)
    return stage

@pytest.fixture()
def test_lead(session, test_sales, test_company, test_stage):
    lead = models.Lead(
        name="Ali Khan", email="ali@test.com", phone="03001234567", company="ABC Ltd",
        stage_id=test_stage.id, owner_id=test_sales.id, company_id=test_company.id,
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead

@pytest.fixture()
def test_lead_admin(session, test_admin, test_company, test_stage):
    lead = models.Lead(
        name="Admin Lead", email="adminlead@test.com", phone="03001234568", company="Admin Co",
        stage_id=test_stage.id, owner_id=test_admin.id, company_id=test_company.id,
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead

@pytest.fixture()
def test_note(session, test_lead, test_sales):
    note = models.Note(content="This is a test note", lead_id=test_lead.id, user_id=test_sales.id)
    session.add(note)
    session.commit()
    session.refresh(note)
    return note

@pytest.fixture()
def test_team(session, test_company, test_manager):
    team = models.Team(name="Test Team", company_id=test_company.id, manager_id=test_manager.id)
    session.add(team)
    session.commit()
    session.refresh(team)
    return team