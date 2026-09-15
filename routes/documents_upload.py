from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from crud.subject_manager import get_subject
from database import get_db
from routes.document import process_documents_pipeline
from crud.ingestion_manager import create_ingestion_job
from utils.logging import get_logger, log_error
import tempfile
import os
from typing import List

router = APIRouter(prefix="/documents", tags=["document-upload"])
logger = get_logger(__name__)


@router.post("/upload/{subject_id}", status_code=202)
async def upload_documents_to_subject(
    subject_id: str,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload multiple documents to a subject.
    Matches frontend call pattern: /documents/upload/{subject_id}
    """
    try:
        subject = get_subject(db, subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        file_metadata = []
        total_size = 0
        
        for file in files:
            content = await file.read()
            file_size = len(content)
            total_size += file_size
            await file.seek(0)
            
            file_metadata.append({
                "filename": file.filename,
                "size": file_size,
                "content_type": file.content_type
            })

        job = create_ingestion_job(
            db=db,
            subject_id=str(subject_id),
            total_files=len(files),
            file_metadata=file_metadata
        )

        temp_dir = tempfile.mkdtemp(prefix=f"ingestion_{job.id}_")
        
        file_paths = []
        for file in files:
            file_path = os.path.join(temp_dir, file.filename)
            content = await file.read()
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            file_paths.append(file_path)

        background_tasks.add_task(
            process_documents_pipeline,
            str(job.id),
            file_paths,
            str(subject_id),
            temp_dir
        )

        logger.info(f"Started bulk upload job {job.id} for {len(files)} files")

        return {
            "job_id": str(job.id),
            "status": "queued",
            "total_files": len(files),
            "total_size": total_size,
            "message": "Upload started successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, {
            "subject_id": str(subject_id),
            "file_count": len(files) if files else 0
        })
        raise HTTPException(status_code=500, detail="Failed to start upload processing")