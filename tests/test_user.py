from app import schemas, models
import time
from jose import jwt
from unittest.mock import patch, AsyncMock
from app.config import settings
from datetime import datetime, timezone, timedelta
import pytest


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200


# REGISTER


def test_register_success(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "password123",
            "full_name": "New User",
            "company_name": "New User Co"
        })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "admin"   
    assert data["company"]["name"] == "New User Co"
    assert data["is_verified"] is False
    assert "id" in data


def test_register_creates_separate_company_per_signup(client):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res1 = client.post("/api/v1/auth/register", json={
            "email": "founder1@test.com", "password": "password123",
            "full_name": "Founder One", "company_name": "Company One"
        })
        res2 = client.post("/api/v1/auth/register", json={
            "email": "founder2@test.com", "password": "password123",
            "full_name": "Founder Two", "company_name": "Company Two"
        })
    assert res1.json()['company']['id'] != res2.json()['company']['id']


def test_register_creates_email_verification_token(client, session):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/register", json={
            "email": "tokentest@test.com", "password": "password123",
            "full_name": "Token Test", "company_name": "Token Co"
        })
    user_id = res.json()['id']
    token = session.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user_id
    ).first()
    assert token is not None
    assert token.expires_at > datetime.now(timezone.utc)


def test_register_duplicate_email_returns_400(client, test_sales):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/register", json={
            "email": "sales@test.com", "password": "password123",
            "full_name": "Duplicate", "company_name": "Dup Co"
        })
    assert res.status_code == 400


def test_register_duplicate_email_case_insensitive(client, test_sales):
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/register", json={
            "email": "SALES@TEST.COM", "password": "password123",
            "full_name": "Case Dup", "company_name": "Case Co"
        })
    assert res.status_code == 400


def test_register_invalid_email(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "notanemail", "password": "password123",
        "full_name": "Test User", "company_name": "Test Co"
    })
    assert res.status_code == 422


def test_register_short_password(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "testuser@gmail.com", "password": "short",
        "full_name": "Test User", "company_name": "Test Co"
    })
    assert res.status_code == 422


def test_register_missing_email(client):
    res = client.post("/api/v1/auth/register", json={
        "password": "password123", "full_name": "Test User", "company_name": "Test Co"
    })
    assert res.status_code == 422


def test_register_missing_password(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "testuser@gmail.com", "full_name": "Test User", "company_name": "Test Co"
    })
    assert res.status_code == 422


def test_register_missing_full_name(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "testuser@gmail.com", "password": "password123", "company_name": "Test Co"
    })
    assert res.status_code == 422


def test_register_missing_company_name(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "testuser@gmail.com", "password": "password123", "full_name": "Test User"
    })
    assert res.status_code == 422


def test_register_empty_body(client):
    res = client.post("/api/v1/auth/register", json={})
    assert res.status_code == 422


def test_register_ignores_client_supplied_role(client):
   
    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/register", json={
            "email": "sneaky@test.com", "password": "password123",
            "full_name": "Sneaky", "company_name": "Sneaky Co", "role": "sales"
        })
    assert res.status_code == 201
    assert res.json()['role'] == "admin" 


def test_register_rollback_on_failure(client, session, monkeypatch):
    

    original_commit = session.commit
    call_count = {"n": 0}

    def failing_commit():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("simulated commit failure")
        return original_commit()

    with patch("app.routers.user.send_welcome_email", new_callable=AsyncMock):
        with patch.object(type(session), "commit", failing_commit):
            res = client.post("/api/v1/auth/register", json={
                "email": "willfail@test.com", "password": "password123",
                "full_name": "Will Fail", "company_name": "Rollback Co"
            })
    assert res.status_code == 500


# LOGIN


def test_login_success(client, test_sales):
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data['token_type'] == "bearer"
    assert data['role'] == "sales"
    assert data['company_id'] == test_sales.company_id


@pytest.mark.parametrize("email, password, status_code", [
    ('wrong@test.com', 'admin123', 403),
    ('admin@test.com', 'wrongpassword', 403),
    (None, 'wrongpassword', 422),
    ('admin@test.com', None, 422),
    (None, None, 422),
])
def test_login_various_bad_inputs(client, test_admin, email, password, status_code):
    res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert res.status_code == status_code


def test_login_admin_success(client, test_admin):
    res = client.post("/api/v1/auth/login", data={"username": "admin@test.com", "password": "admin123"})
    assert res.status_code == 200


def test_login_manager_success(client, test_manager):
    res = client.post("/api/v1/auth/login", data={"username": "manager@test.com", "password": "manager123"})
    assert res.status_code == 200


def test_login_token_contains_correct_company_id(client, test_sales):
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    token = res.json()['access_token']
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload['user_id'] == test_sales.id
    assert payload['company_id'] == test_sales.company_id



# REFRESH TOKEN


def test_refresh_token_success(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    old_access = login_res.json()['access_token']
    old_refresh = login_res.json()['refresh_token']

    res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert res.status_code == 200
    data = res.json()
    assert data['token_type'] == "bearer"
    assert data["access_token"] != old_access
    assert data["refresh_token"] != old_refresh


def test_refresh_invalid_token(client):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": "thisisaninvalidtoken"})
    assert res.status_code == 401


def test_refresh_token_reuse_fails(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    refresh_token = login_res.json()['refresh_token']
    client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401


def test_refresh_token_missing_body(client):
    res = client.post("/api/v1/auth/refresh", json={})
    assert res.status_code == 422


def test_refresh_token_creates_usable_new_access_token(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    old_refresh = login_res.json()['refresh_token']

    res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    new_access = res.json()['access_token']

    leads_res = client.get("/api/v1/leads/", headers={"Authorization": f"Bearer {new_access}"})
    assert leads_res.status_code == 200


# LOGOUT


def test_logout_success(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh},
                      headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 204


def test_logout_revokes_refresh_token(client, test_sales, session):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    client.post("/api/v1/auth/logout", json={"refresh_token": refresh}, headers={"Authorization": f"Bearer {access}"})

    db_token = session.query(models.RefreshToken).filter(models.RefreshToken.token == refresh).first()
    assert db_token.is_revoked is True


def test_logout_token_unusable_after_logout(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    client.post("/api/v1/auth/logout", json={"refresh_token": refresh}, headers={"Authorization": f"Bearer {access}"})
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 401


def test_logout_without_auth_header(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    refresh = login_res.json()['refresh_token']

    res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert res.status_code == 401


def test_logout_with_invalid_refresh_token(client, sales_token):
    res = client.post("/api/v1/auth/logout", json={"refresh_token": "invalidtoken"},
                      headers={"Authorization": f"Bearer {sales_token}"})
    assert res.status_code == 204  



# VERIFY EMAIL


def test_verify_email_success(client, session, test_sales):
    token = models.EmailVerificationToken(
        token="valid-verify-token", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    res = client.get("/api/v1/auth/verify-email?token=valid-verify-token")
    assert res.status_code == 200

    session.refresh(test_sales)
    assert test_sales.is_verified is True


def test_verify_email_invalid_token(client):
    res = client.get("/api/v1/auth/verify-email?token=does-not-exist")
    assert res.status_code == 400


def test_verify_email_expired_token(client, session, test_sales):
    token = models.EmailVerificationToken(
        token="expired-verify-token", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    res = client.get("/api/v1/auth/verify-email?token=expired-verify-token")
    assert res.status_code == 400


def test_verify_email_token_deleted_after_use(client, session, test_sales):
    token = models.EmailVerificationToken(
        token="one-time-verify", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    client.get("/api/v1/auth/verify-email?token=one-time-verify")
    row = session.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.token == "one-time-verify"
    ).first()
    assert row is None


def test_verify_email_token_reuse_fails(client, session, test_sales):
    token = models.EmailVerificationToken(
        token="reuse-verify-token", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    client.get("/api/v1/auth/verify-email?token=reuse-verify-token")
    res = client.get("/api/v1/auth/verify-email?token=reuse-verify-token")
    assert res.status_code == 400


def test_verify_email_missing_token_param(client):
    res = client.get("/api/v1/auth/verify-email")
    assert res.status_code == 422


def test_unverified_user_can_still_log_in(client, test_sales, session):
    test_sales.is_verified = False
    session.commit()
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    assert res.status_code == 200


# FORGOT PASSWORD


def test_forgot_password_existing_email_returns_202(client, test_sales):
    with patch("app.utils.email.send_password_reset_email", new_callable=AsyncMock):
        res = client.post("/api/v1/auth/forgot-password", json={"email": "sales@test.com"})
    assert res.status_code == 202
    assert "detail" in res.json()


def test_forgot_password_creates_reset_token(client, session, test_sales):
    with patch("app.utils.email.send_password_reset_email", new_callable=AsyncMock):
        client.post("/api/v1/auth/forgot-password", json={"email": "sales@test.com"})

    token = session.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == test_sales.id
    ).first()
    assert token is not None
    assert token.is_used is False


def test_forgot_password_missing_email_field(client):
    res = client.post("/api/v1/auth/forgot-password", json={})
    assert res.status_code == 422


def test_forgot_password_nonexistent_email(client):

    res = client.post("/api/v1/auth/forgot-password", json={"email": "doesnotexist@test.com"})
    assert res.status_code == 202



# RESET PASSWORD


def test_reset_password_success(client, session, test_sales):
    token = models.PasswordResetToken(
        token="valid-reset-token", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    res = client.post("/api/v1/auth/reset-password", json={
        "token": "valid-reset-token", "new_password": "newpassword123"
    })
    assert res.status_code == 200

    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "newpassword123"})
    assert login_res.status_code == 200


def test_reset_password_old_password_stops_working(client, session, test_sales):
    token = models.PasswordResetToken(
        token="reset-old-fails", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    client.post("/api/v1/auth/reset-password", json={"token": "reset-old-fails", "new_password": "brandnewpass123"})
    res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    assert res.status_code == 403


def test_reset_password_invalid_token(client):
    res = client.post("/api/v1/auth/reset-password", json={"token": "garbage", "new_password": "whatever123"})
    assert res.status_code == 400


def test_reset_password_expired_token(client, session, test_sales):
    token = models.PasswordResetToken(
        token="expired-reset", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    res = client.post("/api/v1/auth/reset-password", json={"token": "expired-reset", "new_password": "whatever123"})
    assert res.status_code == 400


def test_reset_password_already_used_token(client, session, test_sales):
    token = models.PasswordResetToken(
        token="used-reset-token", user_id=test_sales.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    session.add(token)
    session.commit()

    client.post("/api/v1/auth/reset-password", json={"token": "used-reset-token", "new_password": "firstchange123"})
    res = client.post("/api/v1/auth/reset-password", json={"token": "used-reset-token", "new_password": "secondchange123"})
    assert res.status_code == 400


def test_reset_password_missing_fields(client):
    res = client.post("/api/v1/auth/reset-password", json={})
    assert res.status_code == 422



# SESSIONS


def test_list_sessions_shows_active(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']

    res = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_sessions_no_raw_token_exposed(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']

    res = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access}"})
    for entry in res.json():
        assert "token" not in entry


def test_list_sessions_unauthenticated(client):
    res = client.get("/api/v1/auth/sessions")
    assert res.status_code == 401


def test_list_sessions_excludes_revoked(client, test_sales, session):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']
    refresh = login_res.json()['refresh_token']

    before = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access}"}).json()
    client.post("/api/v1/auth/logout", json={"refresh_token": refresh}, headers={"Authorization": f"Bearer {access}"})

    login_res2 = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access2 = login_res2.json()['access_token']
    after = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access2}"}).json()

    before_ids = {s['id'] for s in before}
    after_ids = {s['id'] for s in after}
    assert before_ids.isdisjoint(after_ids)   # the logged-out session must not reappear


def test_revoke_all_sessions(client, test_sales, session):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']

    res = client.post("/api/v1/auth/sessions/revoke-all", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 204

    active = session.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == test_sales.id, models.RefreshToken.is_revoked == False
    ).count()
    assert active == 0


def test_revoke_single_session(client, test_sales, session):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']

    sessions_res = client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {access}"})
    session_id = sessions_res.json()[0]['id']

    res = client.delete(f"/api/v1/auth/sessions/{session_id}", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 204

    row = session.query(models.RefreshToken).filter(models.RefreshToken.id == session_id).first()
    assert row.is_revoked is True


def test_revoke_other_users_session_rejected(client, test_sales, test_sales2):
    login1 = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    login2 = client.post("/api/v1/auth/login", data={"username": "sales2@test.com", "password": "sales123"})
    access2 = login2.json()['access_token']

    sessions1 = client.get("/api/v1/auth/sessions",
                          headers={"Authorization": f"Bearer {login1.json()['access_token']}"})
    session1_id = sessions1.json()[0]['id']

    res = client.delete(f"/api/v1/auth/sessions/{session1_id}", headers={"Authorization": f"Bearer {access2}"})
    assert res.status_code == 404


def test_revoke_session_not_found(client, test_sales):
    login_res = client.post("/api/v1/auth/login", data={"username": "sales@test.com", "password": "sales123"})
    access = login_res.json()['access_token']

    res = client.delete("/api/v1/auth/sessions/99999", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 404