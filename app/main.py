from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from uuid import uuid4
import os
import asyncio
from .logger import logger
from .worker import process_file
from .database import async_db as db, retry_with_backoff_mongo
from .cache import redis_client, retry_with_backoff

app = FastAPI()
UPLOAD_DIRECTORY = "/app/uploads"

# Ensure upload directory exists
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)

@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )

@app.post("/jobs/")
async def create_job(file: UploadFile = File(...)):
    if not file.filename.endswith(('.txt', '.log')):
        raise ValueError("Unsupported file type")

    job_id = str(uuid4())
    file_path = os.path.join(UPLOAD_DIRECTORY, f"{job_id}_{file.filename}")

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # Read in chunks
                if not chunk:
                    break
                buffer.write(chunk)

        await retry_with_backoff_mongo(
            db.jobs.insert_one,
            {"_id": job_id, "file_name": file.filename, "status": "pending", "progress": 0}
        )

        process_file.delay(job_id, file_path)

    except Exception as e:
        logger.error(f"Failed to create job {job_id}: {e}")
        return {"error": "Failed to process the uploaded file."}

    return {"job_id": job_id, "message": "Job created successfully. Check progress via WebSocket."}


@app.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        while True:
            # Try to get progress from Redis first
            progress = retry_with_backoff(redis_client.hget, f"job:{job_id}", "progress")

            # await websocket.send_json({"redis": progress})
            if progress is None:
                # print("from mongo")
                # await websocket.send_json({"mongo": "mongo"})
                
                # Fallback to MongoDB if Redis data is unavailable
                job = await retry_with_backoff_mongo(
                        db.jobs.find_one,
                        {"_id": job_id}
                    )
                progress = job.get("progress", 0)
                # Optionally repopulate Redis cache for next time
                retry_with_backoff(redis_client.hset, f"job:{job_id}", "progress", progress)

            await websocket.send_json({"job_id": job_id, "progress": float(progress)})

            # Check for job completion
            status = retry_with_backoff(redis_client.hget, f"job:{job_id}", "status")
            if status is None:
                # Fallback to MongoDB if Redis data is unavailable
                job = await retry_with_backoff_mongo(
                        db.jobs.find_one,
                        {"_id": job_id}
                    )
                status = job.get("status", "in_progress")

            if status == "completed":
                await websocket.close()

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.error(f"WebSocket disconnected for job_id {job_id}")
