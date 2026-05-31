import os
import uuid
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import shutil
from pathlib import Path
from pdf_to_json import convert

app = FastAPI()

# Mount static files to serve the frontend
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory task tracker: {task_id: {"status": "pending"|"processing"|"completed"|"failed", "result_file": path, "error": str}}
tasks = {}

def process_pdf(task_id: str, pdf_path: str):
    try:
        tasks[task_id]["status"] = "processing"
        
        output_path = str(Path(pdf_path).with_suffix(".json"))
        # Call the refactored convert function in silent mode
        result_path = convert(pdf_path, output_path, silent=True)
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result_file"] = result_path
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


@app.post("/api/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "File must be a PDF"})
        
    task_id = str(uuid.uuid4())
    
    # Save the file temporarily
    file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    tasks[task_id] = {
        "status": "pending",
        "result_file": None,
        "error": None,
        "filename": file.filename
    }
    
    # Start the background processing
    background_tasks.add_task(process_pdf, task_id, str(file_path))
    
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    if task_id not in tasks:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "filename": task.get("filename"),
        "error": task.get("error")
    }


@app.get("/api/download/{task_id}")
async def download_file(task_id: str):
    if task_id not in tasks:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
        
    task = tasks[task_id]
    if task["status"] != "completed" or not task["result_file"]:
        return JSONResponse(status_code=400, content={"error": "File is not ready yet"})
        
    original_filename = task.get("filename", "converted.pdf")
    json_filename = Path(original_filename).with_suffix(".json").name
    
    return FileResponse(
        path=task["result_file"], 
        filename=json_filename,
        media_type="application/json"
    )

@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=True)
