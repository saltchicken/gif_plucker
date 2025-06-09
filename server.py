import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configuration
MEDIA_FOLDER = "/home/saltchicken/remote/output"

app = FastAPI()

# Allow frontend to call backend (optional, but helpful in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve files at /media/filename
app.mount("/media", StaticFiles(directory=MEDIA_FOLDER), name="media")

@app.get("/")
def index():
    # Optional: serve HTML directly for quick testing
    return FileResponse("index.html", media_type="text/html")

@app.get("/media-list")
def list_media():
    try:
        files = [
            f for f in os.listdir(MEDIA_FOLDER)
            if f.lower().endswith((".gif", ".mp4"))
        ]
        files.sort(key=str.lower)
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete/{filename}")
def delete_file(filename: str):
    safe_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))
    if not safe_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        os.remove(safe_path)
        # Optional: try to delete .png preview if it's a .gif
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
