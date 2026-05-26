import os 
import uuid
from fastapi import HTTPException, status, UploadFile

ALLOWED_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

MAX_FILE_SIZE = 5 * 1024 * 1024
UPLOAD_DIR = "uploads"

def validate_file(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail = f"file of {file.content_type} is not allowed.")
    
async def save_file(file: UploadFile, lead_id: int):
    validate_file(file)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail = f"file exceeds 5MB limit.")
    lead_folder = os.path.join(UPLOAD_DIR, f"lead_{lead_id}")
    os.makedirs(lead_folder, exist_ok=True)
    
    extension = file.filename.split(".")[-1] # type: ignore
    unique_name = f"{uuid.uuid4()}.{extension}"
    filepath = os.path.join(lead_folder, unique_name)

    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "filename": file.filename,
        "filepath": filepath,
        "filetype": file.content_type,
        "filesize": len(content)
    }

def delete_file(filepath: str):
    if os.path.exists(filepath):
        os.remove(filepath)