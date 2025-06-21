from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv, find_dotenv

app = FastAPI()

MEDIA_FOLDER = "/home/saltchicken/remote/output"
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    MEDIA_FOLDER = os.getenv("MEDIA_FOLDER", MEDIA_FOLDER)
else:
    print("No .env file found, using default MEDIA_FOLDER")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the media files at /media/*
app.mount("/media", StaticFiles(directory=MEDIA_FOLDER), name="media")


# Serve the frontend
@app.get("/")
def serve_index():
    return FileResponse("index.html")


# Endpoint to return a paginated list of .gif and .mp4 files
@app.get("/media-list")
def media_list(offset: int = Query(0), limit: int = Query(20)):
    try:
        files = [
            f for f in os.listdir(MEDIA_FOLDER) if f.lower().endswith((".gif", ".mp4"))
        ]
        files.sort(key=lambda x: x.lower())  # sort alphabetically
        total = len(files)
        items = files[offset : offset + limit]
        return {"total": total, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint to delete a file (also deletes .png if it's a .gif)
@app.delete("/delete/{filename}")
def delete_file(filename: str):
    safe_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))
    if not safe_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        os.remove(safe_path)
        # Also try to remove corresponding .png for .gif files
        if filename.lower().endswith(".gif"):
            try:
                os.remove(safe_path.replace(".gif", ".png"))
            except FileNotFoundError:
                pass
        return {"message": f"{filename} deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
