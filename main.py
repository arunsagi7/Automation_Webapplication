import asyncio
import sys
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from services.browser import open_website
from services.db_service import get_all_results # New helper needed
import shutil

# Windows ProactorEventLoop Fix
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

app = FastAPI()

# --- CORS CONFIGURATION ---
# Necessary for Lovable/React frontend to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
for folder in ["screenshots", "input_images"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

@app.get("/")
def home():
    return {"status": "backend_online"}

# 1. API: Get Processing History
@app.get("/results")
async def get_results():
    results = await asyncio.to_thread(get_all_results)
    return results

# 2. API: Upload Creatives
@app.post("/upload-creatives")
async def upload_creatives(files: List[UploadFile] = File(...)):
    saved_files = []
    for file in files:
        file_path = os.path.join("input_images", file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)
    return {"status": "success", "uploaded": saved_files}

# 3. API: Trigger Process (POST version)
@app.post("/process")
async def process_urls(data: dict):
    urls = data.get("urls", [])
    if not urls:
        return {"status": "error", "message": "No URLs provided"}
    
    # Run automation
    result = await open_website(urls=urls)
    return result

# Legacy endpoint for backward compatibility
@app.get("/test")
async def test(urls: str = None):
    url_list = None
    if urls:
        url_list = [u.strip() for u in urls.split(",")]
    return await open_website(urls=url_list)