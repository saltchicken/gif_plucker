import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from pathlib import Path

app = FastAPI()

GIF_FOLDER = Path('/home/saltchicken/remote/output')

# Optional: allow frontend JS access (like from index.html)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r") as f:
        return f.read()

@app.get("/gifs")
async def list_gifs():
    try:
        files = [f.name for f in GIF_FOLDER.iterdir() if f.suffix.lower() == ".gif"]
        return JSONResponse(files)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="GIF folder not found")

@app.get("/gifs/{filename:path}")
async def get_gif(filename: str):
    gif_path = GIF_FOLDER / filename
    if gif_path.exists() and gif_path.suffix.lower() == ".gif":
        return FileResponse(gif_path)
    raise HTTPException(status_code=404, detail="GIF not found")

@app.delete("/delete/{filename:path}")
async def delete_gif(filename: str):
    safe_path = os.path.normpath(os.path.join(GIF_FOLDER, filename))
    if not safe_path.startswith(str(GIF_FOLDER.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    try:
        os.remove(safe_path)
        try:
            os.remove(safe_path.replace('.gif', '.png'))
        except FileNotFoundError:
            pass
        return "", 204
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
