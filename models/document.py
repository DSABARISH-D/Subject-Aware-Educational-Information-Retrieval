from sqlalchemy import Column, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from database import Base, IS_SQLITE


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String if IS_SQLITE else UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()) if IS_SQLITE else uuid.uuid4)
    name = Column(String, nullable=False)
    content = Column(LargeBinary, nullable=False)
    subject_id = Column(String if IS_SQLITE else UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    content_hash = Column(String(64), nullable=True)
    source_type = Column(String(20), nullable=False, default="student", server_default="student")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subject = relationship("Subject")
    
    def __repr__(self):
        return f"<Document {self.name}>"
