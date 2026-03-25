import os
import uuid
import json
import shutil
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.responses import FileResponse

app = FastAPI()

# ------------------------
# Cesty
# ------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_PATH = os.path.join(BASE_DIR, "storage")
METADATA_FILE = os.path.join(BASE_DIR, "metadata.json")

os.makedirs(STORAGE_PATH, exist_ok=True)

if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump([], f)


# ------------------------
# Pomocné funkce
# ------------------------

def load_metadata():
    try:
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_user(user_id: str):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-ID header")
    return user_id


# ------------------------
# 1. Upload souboru
# ------------------------

@app.post("/files/upload")
def upload_file(
    file: UploadFile = File(...),
    x_user_id: str = Header(None)
):
    user_id = get_user(x_user_id)

    file_id = str(uuid.uuid4())
    user_dir = os.path.join(STORAGE_PATH, user_id)

    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file_id)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size = os.path.getsize(file_path)

    metadata = load_metadata()

    file_record = {
        "id": file_id,
        "user_id": user_id,
        "filename": file.filename,
        "path": file_path,
        "size": size,
        "created_at": datetime.utcnow().isoformat()
    }

    metadata.append(file_record)
    save_metadata(metadata)

    return {
        "id": file_id,
        "user_id": user_id,
        "filename": file.filename,
        "size": size
    }


# ------------------------
# 2. Seznam souborů
# ------------------------

@app.get("/files")
def list_files(x_user_id: str = Header(None)):
    user_id = get_user(x_user_id)
    metadata = load_metadata()

    return [f for f in metadata if f["user_id"] == user_id]


# ------------------------
# 3. Stažení souboru
# ------------------------

@app.get("/files/{file_id}")
def download_file(file_id: str, x_user_id: str = Header(None)):
    user_id = get_user(x_user_id)
    metadata = load_metadata()

    file = next((f for f in metadata if f["id"] == file_id), None)

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(path=file["path"], filename=file["filename"])


# ------------------------
# 4. Smazání souboru
# ------------------------

@app.delete("/files/{file_id}")
def delete_file(file_id: str, x_user_id: str = Header(None)):
    user_id = get_user(x_user_id)
    metadata = load_metadata()

    file = next((f for f in metadata if f["id"] == file_id), None)

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    if os.path.exists(file["path"]):
        os.remove(file["path"])

    metadata = [f for f in metadata if f["id"] != file_id]
    save_metadata(metadata)

    return {"message": "File deleted"}
