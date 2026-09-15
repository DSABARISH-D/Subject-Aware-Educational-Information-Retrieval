from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base, IS_SQLITE


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    
    id = Column(String if IS_SQLITE else UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()) if IS_SQLITE else uuid.uuid4)
    subject_id = Column(String if IS_SQLITE else UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    total_files = Column(Integer, default=0, nullable=False)
    processed_files = Column(Integer, default=0, nullable=False)
    failed_files = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    error_message = Column(Text)
    job_metadata = Column(JSON if IS_SQLITE else JSONB)
    
    subject = relationship("Subject")
    
    def __repr__(self):
        return f"<IngestionJob {self.id} - {self.status}>"
    
    @property
    def progress_percentage(self):
        if self.total_files == 0:
            return 0
        return round((self.processed_files / self.total_files) * 100, 1)
    
    @property
    def success_rate(self):
        if self.processed_files == 0:
            return 0
        successful_files = self.processed_files - self.failed_files
        return round((successful_files / self.processed_files) * 100, 1)