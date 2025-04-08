from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import shutil
from pathlib import Path
from typing import List
import tempfile

from demucs_processor import process_audio_files

app = FastAPI(title="Demucs Audio Processor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for uploads and processed files
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Demucs Audio Processing API"}

@app.post("/process")
async def process_audio(
    background_tasks: BackgroundTasks,
    vocal_file: UploadFile = File(...),
    beat_file: UploadFile = File(...),
):
    # Generate a unique ID for this processing job
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    # Save uploaded files
    vocal_path = job_dir / f"vocal_{vocal_file.filename}"
    beat_path = job_dir / f"beat_{beat_file.filename}"
    
    try:
        with open(vocal_path, "wb") as f:
            shutil.copyfileobj(vocal_file.file, f)
        
        with open(beat_path, "wb") as f:
            shutil.copyfileobj(beat_file.file, f)
            
        # Process the files with Demucs (this will run in the background)
        output_dir = PROCESSED_DIR / job_id
        background_tasks.add_task(
            process_audio_files,
            str(vocal_path),
            str(beat_path),
            str(output_dir)
        )
        
        return {
            "job_id": job_id,
            "message": "Audio processing started",
            "status_endpoint": f"/status/{job_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")

@app.get("/status/{job_id}")
async def check_status(job_id: str):
    output_dir = PROCESSED_DIR / job_id
    
    if not output_dir.exists():
        return {"status": "processing", "job_id": job_id}
    
    result_file = output_dir / "combined.mp3"
    if result_file.exists():
        return {
            "status": "completed",
            "job_id": job_id,
            "download_url": f"/download/{job_id}"
        }
    
    return {"status": "processing", "job_id": job_id}

@app.get("/download/{job_id}")
async def download_result(job_id: str):
    output_file = PROCESSED_DIR / job_id / "combined.mp3"
    
    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=output_file,
        filename="demucs_processed.mp3",
        media_type="audio/mpeg"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)