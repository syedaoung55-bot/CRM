
import io
import app.utils.file_handler as files
from app import models


# Note Tests

# Create Note


def test_create_note_success(sales_client, test_lead):
    res = sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "called customer today"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['content'] == "called customer today"
    assert data['id'] == test_lead.id
    assert "user" in data
    assert "id" in data
    assert "created_at" in data


def test_create_note_unauthenticated(client, test_lead):
    res = client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "unauthenticated note"
    })
    assert res.status_code == 401


def test_create_note_not_found(sales_client, test_lead):
    res = sales_client.post("/leads/9999/notes", json={
        "content": "no note"
    })
    assert res.status_code == 404


def test_create_note_empty_content(sales_client, test_lead):
    res = sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": ""
    })
    assert res.status_code == 422


def test_create_note_content_too_long(sales_client, test_lead):
    # max_length=1000 in schema
    res = sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "x" * 1001
    })
    assert res.status_code == 422


def test_create_note_max_length(sales_client, test_lead):
    # max_length=1000 in schema
    res = sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "x" * 1000
    })
    assert res.status_code == 201


def test_create_note_missing_content(sales_client, test_lead):
    res = sales_client.post(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 422


def test_create_note_by_admin(admin_client, test_lead):
    res = admin_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "created by admin"
    })
    assert res.status_code == 201


def test_create_note_by_manager(manager_client, test_lead):
    res = manager_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "created by manager"
    })
    assert res.status_code == 201


def test_create_note_user_id_set_from_token(sales_client, test_lead, test_sales):
    res = sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "check user id"
    })
    assert res.status_code == 201
    assert res.json()['id'] == test_sales.id


def test_create_note_activity_log(sales_client, test_lead, session):
    sales_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "activity log test note"
    })
    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "New Note Created.").first()
    assert log is not None


# Get Notes


def test_get_note_user_success(sales_client, test_lead, test_note):
    res = sales_client.get(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) >= 1


def test_get_notes_only_own_notes(sales_client, sales2_client,
                                   test_lead, test_note, session):
    res = sales_client.get(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    for note in res.json():
        assert "user" in note


def test_get_notes_empty(sales_client, test_lead):
    res = sales_client.get(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 200
    assert res.json() == []


def test_get_note_not_found(sales_client):
    res = sales_client.get("/leads/9999/notes")
    assert res.status_code == 404


def test_get_note_unauthenticated(client, test_lead):
    res = client.get(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 401


def test_get_notes_orders_newest_first(sales_client, test_lead):
    sales_client.post(f"/leads/{test_lead.id}/notes", json={"content": "First note"})
    sales_client.post(f"/leads/{test_lead.id}/notes", json={"content": "Second note"})
    res = sales_client.get(f"/leads/{test_lead.id}/notes")
    assert res.status_code == 200

    notes = res.json()
    assert len(notes) >= 2
    assert notes[0]['content'] == "Second note"


# Delete Notes Tests


def test_delete_note_success(sales_client, test_lead, test_note):
    res = sales_client.delete(f"/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 204


def test_delete_note_actually_deleted(sales_client, test_lead, test_note, session):
    sales_client.delete(f"/leads/{test_lead.id}/notes/{test_note.id}")
    note = session.query(models.Note).filter(
        models.Note.id == test_note.id).first()
    assert note is None


def test_delete_note_not_owner_forbidden(sales2_client, test_lead, test_note):
    res = sales2_client.delete(f"/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 403


def test_delete_note_not_found(sales_client, test_lead):
    res = sales_client.delete(f"/leads/{test_lead.id}/notes/9999")
    assert res.status_code == 404


def test_delete_note_lead_not_found(sales_client, test_lead, test_note):
    res = sales_client.delete(f"/leads/9999/notes/{test_note.id}")
    assert res.status_code == 404


def test_delete_note_unauthenticated(client, test_lead, test_note):
    res = client.delete(f"/leads/{test_lead.id}/notes/{test_note.id}")
    assert res.status_code == 401


def test_admin_can_delete_own_notes(admin_client, test_lead, session):
    client_res = admin_client.post(f"/leads/{test_lead.id}/notes", json={
        "content": "test admin delete own notes"
    })
    note_id = client_res.json()['id']
    res = admin_client.delete(f"/leads/{test_lead.id}/notes/{note_id}")
    assert res.status_code == 204


# File Upload Tests


def make_test_file(content=b"test content", filename="test.pdf",
                   content_type="application/pdf"):
    return ("file",(filename, io.BytesIO(content), content_type))


# Upload file


def test_upload_file_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 201
    data = res.json()
    assert data['filename'] == "test.pdf"
    assert data['filetype'] == "application/pdf"
    assert data['lead_id'] == test_lead.id
    assert "filesize" in data
    assert "id" in data
    assert "created_at" in data


def test_upload_file_jpeg(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("photo.jpg", io.BytesIO(b"jpeg content"), "image/jpeg")})
    assert res.status_code == 201


def test_upload_file_png(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("image.png", io.BytesIO(b"png content"), "image/png")})
    assert res.status_code == 201


def test_upload_file_invalid_type(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("script.exe", io.BytesIO(b"exe content"), "application/exe")})
    assert res.status_code == 400


def test_upload_file_too_large(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    large_content = b"x" * (6 * 1024 * 1024)
    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("big.pdf", io.BytesIO(large_content), "application/pdf")})
    assert res.status_code == 400


def test_upload_file_not_found(sales_client, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post("/leads/9999/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 404


def test_upload_file_unauthenticated(client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 401


def test_upload_file_user_id_set_from_token(sales_client, 
                                test_lead, test_sales, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    assert res.status_code == 201
    assert res.json()['user_id'] == test_sales.id


def test_upload_file_activity_log_created(sales_client, session,
                                test_lead, test_sales, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"pdf content"), "application/pdf")})
    log = session.query(models.Activity_Log).filter(
        models.Activity_Log.action == "New file uploaded.").first()
    assert log is not None


def test_upload_file_saves_to_disk(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("disk_test.pdf", io.BytesIO(b"disk content"), "application/pdf")})
    lead_folder = tmp_path / f"lead_{test_lead.id}"
    assert lead_folder.exists()
    files_in_folder = list(lead_folder.iterdir())
    assert len(files_in_folder) == 1
    

# Get Files


def test_get_files_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("test.pdf", io.BytesIO(b"content"), "application/pdf")}
    )
    res = sales_client.get(f"/leads/{test_lead.id}/file")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) == 1


def test_get_files_multiple(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("file1.pdf", io.BytesIO(b"content1"), "application/pdf")})
    sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("file2.pdf", io.BytesIO(b"content2"), "application/pdf")})
    res = sales_client.get(f"/leads/{test_lead.id}/file")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
    assert len(res.json()) == 2


def test_get_files_empty_lead(sales_client, test_lead):

    res = sales_client.get(f"/leads/{test_lead.id}/file")
    assert res.status_code == 404


def test_get_files_unauthenticated(client, test_lead):

    res = client.get(f"/leads/{test_lead.id}/file")
    assert res.status_code == 401


def test_get_files_not_found(sales_client):

    res = sales_client.get("/leads/9999/file")
    assert res.status_code == 404


# Delete Files


def test_delete_file_success(sales_client, test_lead, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    upload_res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("delete_me.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    res = sales_client.delete(f"/leads/{test_lead.id}/file/{file_id}")
    assert res.status_code == 204


def test_delete_file_actually_deleted(sales_client, test_lead, tmp_path, monkeypatch, session):
    monkeypatch.setattr(files, "UPLOAD_DIR", str(tmp_path))

    upload_res = sales_client.post(f"/leads/{test_lead.id}/file",
        files={"file": ("delete_check.pdf", io.BytesIO(b"content"), "application/pdf")})
    file_id = upload_res.json()['id']
    res = sales_client.delete(f"/leads/{test_lead.id}/file/{file_id}")

    file = session.query(models.LeadFile).filter(
        models.LeadFile.id == file_id).first()
    assert file is None


def test_delete_files_empty_lead(sales_client, test_lead):

    res = sales_client.delete(f"/leads/{test_lead.id}/file/1")
    assert res.status_code == 404


def test_delete_files_unauthenticated(client, test_lead):

    res = client.delete(f"/leads/{test_lead.id}/file/1")
    assert res.status_code == 401


def test_delete_files_not_found(sales_client):

    res = sales_client.delete("/leads/9999/file/9999")
    assert res.status_code == 404