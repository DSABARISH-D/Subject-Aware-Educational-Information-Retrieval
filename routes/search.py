from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crud.search_manager import search_chunks
from crud.subject_manager import get_subject
from database import get_db
from schemas import SearchQuery, SearchResult
import uuid
from typing import List

router = APIRouter(prefix="/subjects/{subject_id}/search", tags=["search"])


@router.post("/", response_model=List[SearchResult])
async def search(
    subject_id: uuid.UUID,
    query: SearchQuery,
    db: Session = Depends(get_db),
):
    """
    Search for chunks in a subject.
    """
    subject = get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    return search_chunks(db=db, subject_id=subject_id, query=query.text)
