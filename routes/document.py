from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from crud.document_manager import (
    create_document as create_document_crud,
    get_documents_by_subject,
)
from crud.subject_manager import get_subject
from crud.ingestion_manager import (
    create_ingestion_job,
    update_job_status,
    increment_job_progress,
    add_file_error
)
from database import get_db
from models.document import Document
from models.chunk import Chunk as ChunkModel
from schemas import Document as DocumentSchema, DocumentCreate
from rag.document_processors import process_document
from rag.ingestion import ingest_file
from utils.logging import get_logger, log_document_upload, log_error
import uuid
import time
import os
import tempfile
from typing import List

router = APIRouter(prefix="/subjects/{subject_id}/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post("/", response_model=DocumentSchema)
async def upload_document(
    subject_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a document to a subject.
    """
    start_time = time.time()
    
    try:
        subject = get_subject(db, subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        content = await file.read()
        file_size = len(content)
        
        # Process document to extract text
        text, success, file_type = process_document(content, file.filename)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Failed to process file. Supported formats: PDF, DOCX, TXT, MD"
            )
        
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content found in the document"
            )
        
        result = ingest_file(db, content, file.filename, subject_id, "student", logger)
        if result is None:
            db_document = db.query(Document).filter(
                Document.subject_id == subject_id,
                Document.name == file.filename,
            ).order_by(Document.created_at.desc()).first()
            chunks = []
        else:
            db_document = result["document"]
            chunks = [None] * result["chunks"]
        
        # Log successful upload
        processing_time = time.time() - start_time
        log_document_upload(
            logger,
            document_id=str(db_document.id),
            filename=file.filename,
            file_size=file_size,
            processing_time=processing_time,
            chunk_count=len(chunks),
            user_id=str(subject_id)
        )

        return db_document
        
    except HTTPException:
        # Re-raise HTTP exceptions without logging as errors
        raise
    except Exception as e:
        # Log unexpected errors
        log_error(logger, e, {
            "filename": file.filename,
            "subject_id": str(subject_id)
        })
        raise HTTPException(status_code=500, detail="Internal server error during document processing")


@router.get("/", response_model=List[DocumentSchema])
def get_documents(
    subject_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get all documents for a subject.
    """
    subject = get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    documents = get_documents_by_subject(db=db, subject_id=subject_id)
    response = []
    for document in documents:
        chunks = db.query(ChunkModel).filter(ChunkModel.document_id == document.id).all()
        response.append({
            "id": document.id,
            "name": document.name,
            "subject_id": document.subject_id,
            "created_at": document.created_at,
            "source_type": document.source_type,
            "page_count": len({chunk.page_number for chunk in chunks if chunk.page_number is not None}),
            "chunk_count": len(chunks),
        })
    return response


@router.delete("/{document_id}")
def delete_document(
    subject_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Delete a document and all its associated chunks.
    """
    try:
        subject = get_subject(db, subject_id)
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

        document = db.query(Document).filter(
            Document.id == document_id,
            Document.subject_id == subject_id
        ).first()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete all chunks associated with this document
        chunks_deleted = db.query(ChunkModel).filter(
            ChunkModel.document_id == document_id
        ).delete()

        # Delete the document
        db.delete(document)
        db.commit()

        logger.info(f"Deleted document {document_id} and {chunks_deleted} chunks for subject {subject_id}")

        return {
            "message": "Document deleted successfully",
            "document_id": str(document_id),
            "chunks_deleted": chunks_deleted
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, {
            "document_id": str(document_id),
            "subject_id": str(subject_id)
        })
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.post("/upload", status_code=202)
async def upload_multiple_documents(
    subject_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Upload multiple documents to a subject (bulk upload with background processing).
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
            "total_size": total_size
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, e, {
            "subject_id": str(subject_id),
            "file_count": len(files) if files else 0
        })
        raise HTTPException(status_code=500, detail="Failed to start upload processing")


async def process_documents_pipeline(
    job_id: str,
    file_paths: List[str],
    subject_id: str,
    temp_dir: str
):
    """
    Background task to process multiple documents for a subject.
    """
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        update_job_status(db, job_id, "processing")
        logger.info(f"Started processing job {job_id} with {len(file_paths)} files")

        for file_path in file_paths:
            try:
                filename = os.path.basename(file_path)
                logger.info(f"Processing file {filename} for job {job_id}")
                
                await process_single_document_async(
                    db, file_path, subject_id, job_id
                )
                
                increment_job_progress(db, job_id, success=True)
                logger.info(f"Successfully processed {filename} for job {job_id}")

            except Exception as e:
                filename = os.path.basename(file_path)
                error_msg = str(e)
                
                add_file_error(db, job_id, filename, error_msg)
                increment_job_progress(db, job_id, success=False)
                
                log_error(logger, e, {
                    "job_id": job_id,
                    "filename": filename,
                    "subject_id": subject_id
                })

        logger.info(f"Completed processing job {job_id}")

    except Exception as e:
        update_job_status(db, job_id, "failed", str(e))
        log_error(logger, e, {
            "job_id": job_id,
            "subject_id": subject_id
        })
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory for job {job_id}")
        except Exception as e:
            log_error(logger, e, {"job_id": job_id, "temp_dir": temp_dir})
        
        db.close()


async def process_single_document_async(
    db: Session,
    file_path: str,
    subject_id: str,
    job_id: str
):
    """
    Process a single document file.
    """
    with open(file_path, "rb") as f:
        content = f.read()
    
    filename = os.path.basename(file_path)
    file_size = len(content)
    
    start_time = time.time()
    
    text, success, file_type = process_document(content, filename)
    
    if not success:
        raise Exception(f"Failed to process file {filename}. Supported formats: PDF, DOCX, TXT, MD")
    
    if not text.strip():
        raise Exception(f"No text content found in {filename}")
    
    result = ingest_file(db, content, filename, subject_id, "student", logger)
    if result is None:
        logger.info("[SKIP] Student document already indexed: %s", filename)
        return
    db_document = result["document"]
    chunks = [None] * result["chunks"]
    
    processing_time = time.time() - start_time
    log_document_upload(
        logger,
        document_id=str(db_document.id),
        filename=filename,
        file_size=file_size,
        processing_time=processing_time,
        chunk_count=len(chunks),
        user_id=subject_id
    )
