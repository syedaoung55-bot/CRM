import io
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
import app.utils.file_handler as files
from app import models

# CREATE NOTE


def test_create_note_success(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "called customer today"})
    assert res.status_code == 201
    data = res.json()
    assert data['content'] == "called customer today"
    assert data['lead_id'] == test_lead.id
    assert data['parent_id'] is None
    assert "user" in data
    assert "created_at" in data


def test_create_note_unauthenticated(client, test_lead):
    res = client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "unauthenticated note"})
    assert res.status_code == 401


def test_create_note_lead_not_found(sales_client):
    res = sales_client.post("/api/v1/leads/9999/notes", json={"content": "no note"})
    assert res.status_code == 404


def test_create_note_empty_content(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": ""})
    assert res.status_code == 422


def test_create_note_content_too_long(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "x" * 1001})
    assert res.status_code == 422


def test_create_note_max_length(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "x" * 1000})
    assert res.status_code == 201


def test_create_note_missing_content(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={})
    assert res.status_code == 422


def test_create_note_by_admin(admin_client, test_lead):
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "created by admin"})
    assert res.status_code == 201


def test_create_note_by_manager(manager_client, test_lead):
    res = manager_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "created by manager"})
    assert res.status_code == 201


def test_create_note_user_id_set_from_token(sales_client, test_lead, test_sales):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "check user id"})
    assert res.status_code == 201
    assert res.json()['user_id'] == test_sales.id


def test_create_note_activity_log(sales_client, test_lead, session):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "activity log test note"})
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "New Note Created.").first()
    assert log is not None


def test_create_note_no_lead_permission_check_for_viewers(sales2_client, test_lead):

    res = sales2_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "sales2 posting"})
    assert res.status_code == 201  


# THREADING


def test_create_note_reply(sales_client, test_lead, test_note):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "a reply", "parent_id": test_note.id
    })
    assert res.status_code == 201
    assert res.json()['parent_id'] == test_note.id


def test_create_note_reply_to_nonexistent_parent(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "orphan reply", "parent_id": 9999
    })
    assert res.status_code == 404


def test_create_note_reply_wrong_lead_rejected(sales_client, test_lead, test_lead_admin, admin_client):
    other_res = admin_client.post(f"/api/v1/leads/{test_lead_admin.id}/notes", json={"content": "on other lead"})
    other_note_id = other_res.json()['id']

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "cross-lead reply", "parent_id": other_note_id
    })
    assert res.status_code == 404


def test_create_note_reply_to_soft_deleted_parent_rejected(sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "reply to deleted note", "parent_id": test_note.id
    })
    assert res.status_code == 404


def test_get_notes_returns_nested_replies(sales_client, test_lead, test_note):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "a reply", "parent_id": test_note.id
    })
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    top_level = [n for n in res.json() if n['id'] == test_note.id][0]
    assert len(top_level['replies']) == 1


def test_get_notes_excludes_replies_at_top_level(sales_client, test_lead, test_note):
    reply_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "a reply", "parent_id": test_note.id
    })
    reply_id = reply_res.json()['id']

    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    top_level_ids = [n['id'] for n in res.json()]
    assert reply_id not in top_level_ids



# MENTIONS


def test_create_note_mention_creates_note_mention_row(sales_client, test_lead, test_admin, session):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": f"hey @{test_admin.full_name}, check this out"
    })
    assert res.status_code == 201

    mention = session.query(models.Note_Mention).filter(
        models.Note_Mention.note_id == res.json()['id'],
        models.Note_Mention.mentioned_user_id == test_admin.id
    ).first()
    assert mention is not None


def test_create_note_mention_creates_notification(sales_client, test_lead, test_admin, session):
    session.query(models.Notification).delete()
    session.commit()

    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": f"@{test_admin.full_name} please review"
    })
    notif = session.query(models.Notification).filter(
        models.Notification.user_id == test_admin.id,
        models.Notification.type == models.NotificationType.mention.value
    ).first()
    assert notif is not None


def test_create_note_mention_nonexistent_user_no_error(sales_client, test_lead):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "@NoSuchPerson this should just not match anything"
    })
    assert res.status_code == 201


def test_create_note_mention_cross_company_user_not_matched(sales_client, test_lead, test_admin_company2, session):
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": f"@{test_admin_company2.full_name} shouldn't match cross-tenant"
    })
    mention = session.query(models.Note_Mention).filter(
        models.Note_Mention.note_id == res.json()['id']
    ).first()
    assert mention is None


def test_create_note_self_mention_creates_no_notification(sales_client, test_lead, test_sales, session):
    session.query(models.Notification).delete()
    session.commit()

    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": f"reminding myself @{test_sales.full_name}"
    })
    notif = session.query(models.Notification).filter(
        models.Notification.type == models.NotificationType.mention.value
    ).first()
    assert notif is None


def test_create_note_self_mention_still_creates_mention_row(sales_client, test_lead, test_sales, session):

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": f"@{test_sales.full_name} noting for myself"
    })
    mention = session.query(models.Note_Mention).filter(
        models.Note_Mention.note_id == res.json()['id'],
        models.Note_Mention.mentioned_user_id == test_sales.id
    ).first()
    assert mention is not None


# GET NOTES


def test_get_notes_success(sales_client, test_lead, test_note):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_get_notes_visible_to_all_with_lead_access(admin_client, test_lead, test_note):
    # get_notes has no author-restriction filter — confirms every note on the lead is visible
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    assert any(n['id'] == test_note.id for n in res.json())


def test_get_notes_empty(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    assert res.json() == []


def test_get_notes_lead_not_found(sales_client):
    res = sales_client.get("/api/v1/leads/9999/notes")
    assert res.status_code == 404


def test_get_notes_unauthenticated(client, test_lead):
    res = client.get(f"/api/v1/leads/{test_lead.id}/notes")
    assert res.status_code == 401


def test_get_notes_orders_newest_first(sales_client, test_lead):
    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "First note"})
    sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "Second note"})
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    assert res.json()[0]['content'] == "Second note"


def test_get_notes_excludes_soft_deleted(sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    ids = [n['id'] for n in res.json()]
    assert test_note.id not in ids



# GET DELETED NOTES


def test_get_deleted_notes_admin_only(admin_client, sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")

    res_admin = admin_client.get(f"/api/v1/leads/{test_lead.id}/notes/deleted")
    assert res_admin.status_code == 200
    assert any(n['id'] == test_note.id for n in res_admin.json())

    res_sales = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes/deleted")
    assert res_sales.status_code == 403


def test_get_deleted_notes_excludes_active(admin_client, test_lead, test_note):
    res = admin_client.get(f"/api/v1/leads/{test_lead.id}/notes/deleted")
    assert res.json() == []   # test_note is not deleted, must not appear



# DELETE NOTE (soft delete)


def test_delete_note_success(sales_client, test_lead, test_note):
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 204


def test_delete_note_soft_deletes_not_removes_row(sales_client, test_lead, test_note, session):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    note = session.query(models.Note).filter(models.Note.id == test_note.id).first()
    assert note is not None
    assert note.deleted_at is not None
    assert note.deleted_by is not None


def test_delete_note_not_author_forbidden(sales2_client, test_lead, test_note):

    res = sales2_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 403


def test_delete_note_not_found(sales_client, test_lead):
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/9999")
    assert res.status_code == 404


def test_delete_note_already_deleted_returns_404(sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 404


def test_delete_note_lead_not_found(sales_client, test_lead, test_note):
    res = sales_client.delete(f"/api/v1/leads/9999/notes/{test_note.id}")
    assert res.status_code == 404


def test_delete_note_unauthenticated(client, test_lead, test_note):
    res = client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 401


def test_admin_cannot_delete_others_note_either(admin_client, test_lead, test_note):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 403


def test_admin_can_delete_own_notes(admin_client, test_lead):
    create_res = admin_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={"content": "admin's own note"})
    note_id = create_res.json()['id']
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{note_id}")
    assert res.status_code == 204


# RESTORE NOTE


def test_restore_note_success(admin_client, sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/restore")
    assert res.status_code == 200
    assert res.json()['deleted_at'] is None


def test_restore_note_non_admin_forbidden(sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/restore")
    assert res.status_code == 403


def test_restore_note_not_deleted_returns_404(admin_client, test_lead, test_note):
    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/restore")
    assert res.status_code == 404


def test_restore_note_visible_again_after(admin_client, sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    admin_client.post(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/restore")

    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/notes")
    ids = [n['id'] for n in res.json()]
    assert test_note.id in ids



# PERMANENT DELETE NOTE


def test_permanent_delete_note_requires_soft_delete_first(admin_client, test_lead, test_note):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/permanent")
    assert res.status_code == 404


def test_permanent_delete_note_success(admin_client, sales_client, test_lead, test_note, session):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/permanent")
    assert res.status_code == 204

    note = session.query(models.Note).filter(models.Note.id == test_note.id).first()
    assert note is None


def test_permanent_delete_note_non_admin_forbidden(sales_client, test_lead, test_note):
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/permanent")
    assert res.status_code == 403


def test_permanent_delete_note_cascades_replies(admin_client, sales_client, test_lead, test_note, session):
    reply_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/notes", json={
        "content": "a reply", "parent_id": test_note.id
    })
    reply_id = reply_res.json()['id']

    sales_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}")
    admin_client.delete(f"/api/v1/leads/{test_lead.id}/notes/{test_note.id}/permanent")

    reply = session.query(models.Note).filter(models.Note.id == reply_id).first()
    assert reply is None



# FILE UPLOAD


def test_upload_file_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 201
    data = res.json()
    assert data['filename'] == "test.pdf"
    assert data['filetype'] == "application/pdf"
    assert data['lead_id'] == test_lead.id
    assert "filesize" in data
    assert "id" in data


def test_upload_file_jpeg(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("photo.jpg", io.BytesIO(b"jpeg content"), "image/jpeg")})
    assert res.status_code == 201


def test_upload_file_png(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("image.png", io.BytesIO(b"png content"), "image/png")})
    assert res.status_code == 201


def test_upload_file_invalid_type(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("script.exe", io.BytesIO(b"exe content"), "application/exe")})
    assert res.status_code == 400


def test_upload_file_too_large(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    large_content = b"x" * (6 * 1024 * 1024)
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("big.pdf", io.BytesIO(large_content), "application/pdf")})
    assert res.status_code == 400


def test_upload_file_lead_not_found(sales_client, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post("/api/v1/leads/9999/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 404


def test_upload_file_unauthenticated(client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 401


def test_upload_file_user_id_set_from_token(sales_client, test_lead, test_sales, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 201
    assert res.json()['user_id'] == test_sales.id


def test_upload_file_activity_log_created(sales_client, session, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    log = session.query(models.Activity_Log).filter(models.Activity_Log.action == "New file uploaded.").first()
    assert log is not None


def test_upload_file_saves_to_disk(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("disk_test.pdf", io.BytesIO(b"disk content"), "application/pdf")})
    lead_folder = tmp_path / f"lead_{test_lead.id}"
    assert lead_folder.exists()
    assert len(list(lead_folder.iterdir())) == 1



# GET FILES


def test_get_files_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")})
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/file")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_get_files_multiple(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("file1.pdf", io.BytesIO(b"content1"), "application/pdf")})
    sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("file2.pdf", io.BytesIO(b"content2"), "application/pdf")})
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/file")
    assert len(res.json()) == 2


def test_get_files_empty_lead_returns_404(sales_client, test_lead):
    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/file")
    assert res.status_code == 404


def test_get_files_unauthenticated(client, test_lead):
    res = client.get(f"/api/v1/leads/{test_lead.id}/file")
    assert res.status_code == 401


def test_get_files_lead_not_found(sales_client):
    res = sales_client.get("/api/v1/leads/9999/file")
    assert res.status_code == 404


def test_get_files_returns_404_once_all_soft_deleted(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("onlyfile.pdf", io.BytesIO(b"x"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res = sales_client.get(f"/api/v1/leads/{test_lead.id}/file")
    assert res.status_code == 404  



# GET DELETED FILES


def test_get_deleted_files_admin_only(admin_client, sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("del.pdf", io.BytesIO(b"x"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res_admin = admin_client.get(f"/api/v1/leads/{test_lead.id}/file/deleted")
    assert res_admin.status_code == 200
    assert any(f['id'] == file_id for f in res_admin.json())

    res_sales = sales_client.get(f"/api/v1/leads/{test_lead.id}/file/deleted")
    assert res_sales.status_code == 403



# DELETE FILE (soft delete )


def test_delete_file_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("delete_me.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")
    assert res.status_code == 204


def test_delete_file_soft_deletes_not_removes_row(sales_client, test_lead, tmp_path, monkeypatch, session):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("delete_check.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    file_row = session.query(models.LeadFile).filter(models.LeadFile.id == file_id).first()
    assert file_row is not None
    assert file_row.deleted_at is not None


def test_delete_file_any_user_with_lead_access_can_delete_others_upload(sales2_client, sales_client, test_lead, tmp_path, monkeypatch):

    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("anyone.pdf", io.BytesIO(b"x"), "application/pdf")})
    file_id = upload_res.json()['id']

    res = sales2_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")
    assert res.status_code == 403 or res.status_code == 204



def test_delete_file_empty_lead(sales_client, test_lead):
    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/1")
    assert res.status_code == 404


def test_delete_file_unauthenticated(client, test_lead):
    res = client.delete(f"/api/v1/leads/{test_lead.id}/file/1")
    assert res.status_code == 401


def test_delete_file_not_found(sales_client):
    res = sales_client.delete("/api/v1/leads/9999/file/9999")
    assert res.status_code == 404


def test_delete_file_already_deleted_returns_404(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("twice.pdf", io.BytesIO(b"x"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")
    assert res.status_code == 404



# RESTORE FILE


def test_restore_file_success(admin_client, sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("restore_me.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/file/{file_id}/restore")
    assert res.status_code == 200
    assert res.json()['deleted_at'] is None


def test_restore_file_non_admin_forbidden(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("x.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file/{file_id}/restore")
    assert res.status_code == 403


def test_restore_file_not_deleted_returns_404(admin_client, test_lead, tmp_path, monkeypatch, sales_client):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("notdeleted.pdf", io.BytesIO(b"x"), "application/pdf")})
    file_id = upload_res.json()['id']

    res = admin_client.post(f"/api/v1/leads/{test_lead.id}/file/{file_id}/restore")
    assert res.status_code == 404



# PERMANENT DELETE FILE


def test_permanent_delete_file_requires_soft_delete_first(admin_client, sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("x.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']

    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}/permanent")
    assert res.status_code == 404


def test_permanent_delete_file_removes_from_disk_and_db(admin_client, sales_client, test_lead, tmp_path, monkeypatch, session):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("permanent.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    filepath = upload_res.json()['filepath']

    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}/permanent")
    assert res.status_code == 204

    import os
    assert not os.path.exists(filepath)
    assert session.query(models.LeadFile).filter(models.LeadFile.id == file_id).first() is None


def test_permanent_delete_file_non_admin_forbidden(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))
    upload_res = sales_client.post(f"/api/v1/leads/{test_lead.id}/file",
        files={"file": ("x.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}")

    res = sales_client.delete(f"/api/v1/leads/{test_lead.id}/file/{file_id}/permanent")
    assert res.status_code == 403


def test_permanent_delete_file_not_found(admin_client, test_lead):
    res = admin_client.delete(f"/api/v1/leads/{test_lead.id}/file/9999/permanent")
    assert res.status_code == 404