from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crud.chat_manager import get_chat_response
from crud.subject_manager import get_subject
from database import get_db
from schemas import ChatMessage, ChatResponse
import uuid

router = APIRouter(prefix="/subjects/{subject_id}/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    subject_id: uuid.UUID,
    message: ChatMessage,
    db: Session = Depends(get_db),
):
    """
    Chat with a subject's uploaded material.
    """
    subject = get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    try:
        response_data = get_chat_response(db=db, subject_id=subject_id, query=message.text)
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat service error: {str(e)}")
