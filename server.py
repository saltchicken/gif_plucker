from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv, find_dotenv

app = FastAPI()

# ‼️ UPDATED: Changed default path to ComfyUI output directory and expanded user (~)
MEDIA_FOLDER = os.path.expanduser("~/.local/share/ComfyUI/output")
dotenv_path = find_dotenv()
if dotenv_path:
    load_dotenv(dotenv_path)
    MEDIA_FOLDER = os.getenv("MEDIA_FOLDER", MEDIA_FOLDER)
else:
    print(f"No .env file found, using default MEDIA_FOLDER: {MEDIA_FOLDER}")

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
        # ‼️ UPDATED: Recursive file search using os.walk to include subdirectories
        files = []
        for root, _, filenames in os.walk(MEDIA_FOLDER):
            for filename in filenames:
                if filename.lower().endswith((".gif", ".mp4", ".png")):
                    # Create relative path from the base MEDIA_FOLDER
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, MEDIA_FOLDER)
                    files.append(rel_path)

        files.sort(key=lambda x: x.lower())  # sort alphabetically
        total = len(files)
        items = files[offset : offset + limit]
        return {"total": total, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ‼️ UPDATED: Changed to Query parameter to handle paths with slashes safely
@app.delete("/delete")
def delete_file(
    filename: str = Query(..., description="Relative path of file to delete"),
):
    # ‼️ UPDATED: Safe path calculation now handles the relative paths from subdirs
    safe_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))

    # Security check: ensure path is still inside MEDIA_FOLDER
    if not safe_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        if os.path.exists(safe_path):
            os.remove(safe_path)

        # Also try to remove corresponding .png for .gif files
        # ‼️ UPDATED: Logic to handle cleanup of paired files in subdirectories
        if filename.lower().endswith(".gif"):
            png_path = safe_path.replace(".gif", ".png")
            if os.path.exists(png_path):
                os.remove(png_path)

        if filename.lower().endswith(".png"):
            # Check if this was a preview for a gif that might have been deleted?
            # Or just delete the png itself (already done above).
            pass

        return {"message": f"{filename} deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
