import os
import uuid
import json
import shutil
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

STORAGE_PATH = "storage"
METADATA_FILE = "metadata.json"


# ------------------------
# Pomocné funkce
# ------------------------

def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, "r") as f:
        return json.load(f)


def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_current_user():
    return "user_1"  # zatím natvrdo


# ------------------------
# 1. Upload souboru
# ------------------------

@app.post("/files/upload")
def upload_file(file: UploadFile = File(...)):
    user_id = get_current_user()

    file_id = str(uuid.uuid4())
    user_dir = os.path.join(STORAGE_PATH, user_id)

    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file_id)

    # uložit soubor
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
        "filename": file.filename,
        "size": size
    }


# ------------------------
# 2. Seznam souborů
# ------------------------

@app.get("/files")
def list_files():
    user_id = get_current_user()
    metadata = load_metadata()

    user_files = [f for f in metadata if f["user_id"] == user_id]

    return user_files


# ------------------------
# 3. Stažení souboru
# ------------------------

@app.get("/files/{file_id}")
def download_file(file_id: str):
    user_id = get_current_user()
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
def delete_file(file_id: str):
    user_id = get_current_user()
    metadata = load_metadata()

    file = next((f for f in metadata if f["id"] == file_id), None)

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # smazat soubor z disku
    if os.path.exists(file["path"]):
        os.remove(file["path"])

    # odstranit z metadata
    metadata = [f for f in metadata if f["id"] != file_id]
    save_metadata(metadata)

    return {"message": "File deleted"}