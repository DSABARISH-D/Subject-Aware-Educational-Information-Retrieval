from sqlalchemy.orm import Session
from models.subject import Subject
from schemas import SubjectCreate
from database import IS_SQLITE
import uuid
from typing import Union


def create_subject(db: Session, subject: SubjectCreate):
    db_subject = Subject(**subject.model_dump())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


def get_subjects(db: Session):
    return db.query(Subject).all()


def get_subject(db: Session, subject_id: Union[uuid.UUID, str]):
    sid_str = str(subject_id)
    if IS_SQLITE:
        return db.query(Subject).filter(Subject.id == sid_str).first()
    else:
        try:
            val = uuid.UUID(sid_str) if isinstance(subject_id, str) else subject_id
            return db.query(Subject).filter(Subject.id == val).first()
        except Exception:
            return db.query(Subject).filter(Subject.id == sid_str).first()
