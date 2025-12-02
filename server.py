from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import json
from dotenv import load_dotenv, find_dotenv
from PIL import Image

app = FastAPI()


MEDIA_FOLDER = os.path.expanduser("~/.local/share/ComfyUI/output")
SAVED_FOLDER_NAME = "Saved"

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


@app.post("/save")
def save_file(
    filename: str = Query(..., description="Relative path of file to save"),
):
    source_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))

    # Security check: ensure path is still inside MEDIA_FOLDER
    if not source_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Destination folder: MEDIA_FOLDER/Saved
    saved_dir = os.path.join(MEDIA_FOLDER, SAVED_FOLDER_NAME)
    os.makedirs(saved_dir, exist_ok=True)

    base_name = os.path.basename(filename)
    dest_path = os.path.join(saved_dir, base_name)

    # Handle duplicates by appending number (e.g. image_1.png)
    counter = 1
    name, ext = os.path.splitext(base_name)
    while os.path.exists(dest_path):
        dest_path = os.path.join(saved_dir, f"{name}_{counter}{ext}")
        counter += 1

    try:
        # Copy the main file
        shutil.copy2(source_path, dest_path)

        if filename.lower().endswith(".gif"):
            png_source = source_path.replace(".gif", ".png")
            if os.path.exists(png_source):
                # Save the png preview with the same naming logic
                dest_png_path = dest_path.replace(".gif", ".png")
                shutil.copy2(png_source, dest_png_path)

        return {"message": f"Saved to {os.path.relpath(dest_path, MEDIA_FOLDER)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metadata")
def get_metadata(
    filename: str = Query(
        ..., description="Relative path of file to get metadata from"
    ),
    key: str = Query(None, description="Specific metadata key to fetch"),
):
    safe_path = os.path.normpath(os.path.join(MEDIA_FOLDER, filename))

    if not safe_path.startswith(os.path.abspath(MEDIA_FOLDER)):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Try to open with PIL
        with Image.open(safe_path) as img:
            info = img.info


            if key == "prompt_text":
                if "prompt" not in info:
                    return {"found": False, "message": "No prompt data found in image"}

                try:
                    # ComfyUI stores it as a JSON string inside the PNG info
                    prompt_data = json.loads(info["prompt"])

                    found_texts = []

                    # 1. Find all KSampler nodes
                    samplers = [
                        (id, node)
                        for id, node in prompt_data.items()
                        if "Sampler" in node.get("class_type", "")
                    ]

                    for _, sampler in samplers:
                        # 2. Find the 'positive' input (usually a link like ["42", 0])
                        positive_link = sampler.get("inputs", {}).get("positive")

                        if positive_link and isinstance(positive_link, list):
                            from_node_id = positive_link[0]

                            if from_node_id in prompt_data:
                                source_node = prompt_data[from_node_id]

                                # 3. Check if that node has a 'text' input that is a string
                                # (Standard CLIPTextEncode / Prompt Manager behavior)
                                text_val = source_node.get("inputs", {}).get("text")

                                if isinstance(text_val, str) and text_val.strip():
                                    found_texts.append(text_val)

                    if found_texts:
                        # Join unique texts (in case of multiple samplers using same prompt)
                        return {"metadata": "\n\n".join(list(set(found_texts)))}
                    else:
                        # Fallback: Just look for any CLIPTextEncode that isn't negative
                        # (Useful if the sampler logic fails due to complex routing)
                        fallback_texts = []
                        for _, node in prompt_data.items():
                            if "CLIPTextEncode" in node.get("class_type", ""):
                                # Skip if title says negative
                                title = node.get("_meta", {}).get("title", "").lower()
                                if "negative" in title:
                                    continue

                                text_val = node.get("inputs", {}).get("text")
                                if isinstance(text_val, str) and len(text_val) > 5:
                                    fallback_texts.append(text_val)

                        if fallback_texts:
                            return {"metadata": "\n\n".join(list(set(fallback_texts)))}

                        return {
                            "found": False,
                            "message": "Could not identify prompt text in graph",
                        }

                except json.JSONDecodeError:
                    return {"found": False, "message": "Prompt data was not valid JSON"}
                except Exception as e:
                    return {
                        "found": False,
                        "message": f"Error parsing prompt: {str(e)}",
                    }


            if key:
                if key in info:
                    return {"metadata": info[key]}
                else:
                    return {
                        "found": False,
                        "message": f"Metadata key '{key}' not found.",
                    }

            if "workflow" in info:
                return {"metadata": info["workflow"]}
            elif "prompt" in info:
                return {"metadata": info["prompt"]}
            else:
                return {"found": False, "message": "No ComfyUI metadata found"}
    except Exception as e:
        return {"found": False, "message": f"Could not extract metadata: {str(e)}"}