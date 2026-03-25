import os
import uuid
import json
import shutil
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

# ------------------------
# Cesty (FIX na cwd problém)
# ------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_PATH = os.path.join(BASE_DIR, "storage")
METADATA_FILE = os.path.join(BASE_DIR, "metadata.json")

# vytvořit storage složku pokud neexistuje
os.makedirs(STORAGE_PATH, exist_ok=True)

# vytvořit metadata.json pokud neexistuje
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
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print("Chyba při načítání metadata:", e)
        return []


def save_metadata(data):
    try:
        with open(METADATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Chyba při ukládání metadata:", e)


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

    try:
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

        print("Ukládám metadata:", file_record)  # DEBUG

        save_metadata(metadata)

        return {
            "id": file_id,
            "filename": file.filename,
            "size": size
        }

    except Exception as e:
        print("Chyba při uploadu:", e)
        raise HTTPException(status_code=500, detail="Upload failed")


# ------------------------
# 2. Seznam souborů
# ------------------------

@app.get("/files")
def list_files():
    user_id = get_current_user()
    metadata = load_metadata()

    return [f for f in metadata if f["user_id"] == user_id]


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

    if not os.path.exists(file["path"]):
        raise HTTPException(status_code=404, detail="File missing on disk")

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

    try:
        # smazat soubor
        if os.path.exists(file["path"]):
            os.remove(file["path"])

        # smazat metadata
        metadata = [f for f in metadata if f["id"] != file_id]
        save_metadata(metadata)

        return {"message": "File deleted"}

    except Exception as e:
        print("Chyba při mazání:", e)
        raise HTTPException(status_code=500, detail="Delete failed")
