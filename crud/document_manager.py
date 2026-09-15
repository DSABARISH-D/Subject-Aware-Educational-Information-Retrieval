from sqlalchemy.orm import Session
from models.document import Document
from schemas import DocumentCreate
from database import IS_SQLITE
import uuid
from typing import Union


def create_document(db: Session, document: DocumentCreate, subject_id: Union[uuid.UUID, str], content: bytes):
    sid = str(subject_id) if IS_SQLITE else (uuid.UUID(str(subject_id)) if isinstance(subject_id, str) else subject_id)
    db_document = Document(**document.model_dump(), subject_id=sid, content=content)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document


def get_documents_by_subject(db: Session, subject_id: Union[uuid.UUID, str]):
    sid = str(subject_id) if IS_SQLITE else (uuid.UUID(str(subject_id)) if isinstance(subject_id, str) else subject_id)
    return db.query(Document).filter(Document.subject_id == sid).all()
