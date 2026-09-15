from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crud.ingestion_manager import get_ingestion_job, get_jobs_by_subject
from database import get_db

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the status of an ingestion job.
    """
    job = get_ingestion_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": {
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "failed_files": job.failed_files,
            "percentage": job.progress_percentage,
            "success_rate": job.success_rate
        },
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "error_message": job.error_message,
        "metadata": job.job_metadata
    }


@router.get("/subject/{subject_id}")
async def get_subject_jobs(
    subject_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Get recent ingestion jobs for a subject.
    """
    jobs = get_jobs_by_subject(db, subject_id, limit)
    
    return [
        {
            "job_id": str(job.id),
            "subject_id": str(job.subject_id),
            "status": job.status,
            "total_files": job.total_files,
            "processed_files": job.processed_files,
            "failed_files": job.failed_files,
            "progress_percentage": job.progress_percentage,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
        for job in jobs
    ]