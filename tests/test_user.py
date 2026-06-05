from app import schemas, models
import time
from jose import jwt
from unittest.mock import patch, AsyncMock
from app.config import settings
import pytest

# Register Tests 

def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json() == {"Message": "Welcome to my API Practice Project"}


def test_register_success(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "newuser@test.com",
            "password": "password123",
            "full_name": "New User"
        })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "sales"
    assert "id" in data

def test_check_default_role_sales(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "roletest@test.com",
            "password": "password123",
            "full_name": "Role Test"
        })
    assert res.status_code == 201
    assert res.json()['role'] == "sales"


def test_check_duplicate_email(client, test_sales):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "sales@test.com",
            "password": "password123",
            "full_name": "Duplicate"
            })
        assert res.status_code == 500


def test_check_invalid_email(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "notanemail",
            "password": "password123",
            "full_name": "Test User"
            })
        assert res.status_code == 422

    
def test_check_short_password(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "testuser@gmail.com",
            "password": "short",
            "full_name": "Test User"
            })
        assert res.status_code == 422


def test_check_missing_email(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "password": "short",
            "full_name": "Test User"
            })
        assert res.status_code == 422


def test_check_missing_password(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "testuser@gmail.com",
            "full_name": "Test User"
            })
        assert res.status_code == 422


def test_check_missing_full_name(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={
            "email": "testuser@gmail.com",
            "password": "short",
            })
        assert res.status_code == 422


def test_check_empty_body(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/auth/register", json={})
        assert res.status_code == 422


# Login Tests


def test_login_success(client, test_sales):
    res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data['token_type'] == "bearer"


def test_login_return_both_tokens(client, test_sales):
    res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["access_token"] != ""
    assert data["refresh_token"] != ""


@pytest.mark.parametrize("email, password, status_code", [
    ('wrong@gmail.com', 'admin123', 403),
    ('admin@gmail.com', 'wrongpassword', 403),
    ('wrong@gmail.com', 'admin123', 403),
    (None, 'wrongpassword', 422),
    ('admin@gmail.com', None, 422),
    (None, None, 422)
])
def test_incorrect_login(client, admin_client, email , password, status_code):
    res = client.post("/auth/login/", data={
        "username": email, 
        "password": password
        })
    assert res.status_code == status_code


def test_login_admin_success(client, test_admin):
    res = client.post("/auth/login", data={
        "username": "admin@test.com",
        "password": "admin123"
    })
    assert res.status_code == 200


def test_login_manager_success(client, test_manager):
    res = client.post("/auth/login", data={
        "username": "manager@test.com",
        "password": "manager123"
    })
    assert res.status_code == 200


# Refresh Token Tests


def test_refresh_token_success(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    old_access = login_res.json()['access_token']
    old_refresh = login_res.json()['refresh_token']

    time.sleep(3)

    res = client.post("/auth/refresh", json={
        "refresh_token": old_refresh
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data['token_type'] == "bearer"
    assert data["access_token"] != old_access
    assert data["refresh_token"] != old_refresh


def test_refresh_invalid_token(client):
    res = client.post("/auth/refresh", json={
        "refresh_token": "thisisaninvalidtoken"
    })
    assert res.status_code == 401


def test_refresh_token_reuse_fail(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    refresh_token = login_res.json()['refresh_token']
    client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })

    res = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert res.status_code == 401


def test_refresh_token_missing_body(client):
    res = client.post("/auth/refresh", json={})
    assert res.status_code == 422


def test_refresh_token_creates_new_access_token(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    old_access = login_res.json()['access_token']
    old_refresh = login_res.json()['refresh_token']

    time.sleep(3)

    res = client.post("/auth/refresh", json={
        "refresh_token": old_refresh
    })
    new_access = res.json()['access_token']
    leads_res = client.get("leads", 
                headers={"Authorization": f"Bearer {new_access}"})
    assert leads_res.status_code == 200


# Logout Tests


def test_logout_success(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    time.sleep(3)

    res = client.post("/auth/logout", 
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"}
        )
    assert res.status_code == 204


def test_logout_revokes_refresh_token(client, test_sales, session):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    time.sleep(3)

    client.post("/auth/logout", 
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"}
        )
    db_token = session.query(models.RefreshToken).filter(
        models.RefreshToken.token == refresh).first()
    assert db_token.is_revoked == True


def test_logout_token_unusable_after_logout(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    time.sleep(3)

    client.post("/auth/logout", 
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"}
        )
    res = client.post("/auth/refresh", json={
        "refresh_token": refresh
    })
    assert res.status_code == 401

    
def test_logout_without_auth_header(client, test_sales):
    login_res = client.post("/auth/login", data={
        "username": "sales@test.com",
        "password": "sales123"
    })
    refresh = login_res.json()['refresh_token']

    time.sleep(3)

    res = client.post("/auth/logout", 
        json={"refresh_token": refresh},
        )
    assert res.status_code == 401


def test_logout_with_invalid_refresh_token(client, sales_token):
    res = client.post("/auth/logout", 
        json={"refresh_token": "inalidtoken"},
        headers={"Authorization": f"Bearer {sales_token}"}
        )
    assert res.status_code == 204