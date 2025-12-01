from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv, find_dotenv

app = FastAPI()


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



@app.get("/media-list")
def media_list(
    subdir: str = Query("", description="Subdirectory to list"),
    offset: int = Query(0),
    limit: int = Query(20),
):

    base_dir = os.path.abspath(MEDIA_FOLDER)
    target_dir = os.path.abspath(os.path.join(base_dir, subdir))

    if not target_dir.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail="Directory not found")

    try:
        items = []


        with os.scandir(target_dir) as entries:
            for entry in entries:

                if entry.is_dir():
                    # Calculate relative path for navigation
                    rel_path = os.path.relpath(entry.path, MEDIA_FOLDER)
                    items.append({"type": "dir", "name": entry.name, "path": rel_path})
                elif entry.is_file() and entry.name.lower().endswith(
                    (".gif", ".mp4", ".png", ".jpg", ".jpeg", ".webp")
                ):
                    rel_path = os.path.relpath(entry.path, MEDIA_FOLDER)
                    items.append({"type": "file", "name": entry.name, "path": rel_path})


        items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))

        total = len(items)
        paginated_items = items[offset : offset + limit]

        return {"total": total, "items": paginated_items, "current_path": subdir}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete")
def delete_file(
    filename: str = Query(..., description="Relative path of file to delete"),
):
    safe_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))

    # Security check: ensure path is still inside MEDIA_FOLDER
    if not safe_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        if os.path.exists(safe_path):
            os.remove(safe_path)

        # Also try to remove corresponding .png for .gif files

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