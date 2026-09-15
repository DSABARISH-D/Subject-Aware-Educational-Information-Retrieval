from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from database import Base, IS_SQLITE


class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(String if IS_SQLITE else UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()) if IS_SQLITE else uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Subject {self.name}>"
