from sqlalchemy import Column, Text, String, ForeignKey, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
from database import Base, IS_SQLITE


class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(String if IS_SQLITE else UUID(as_uuid=True), primary_key=True, default=lambda: str(uuid.uuid4()) if IS_SQLITE else uuid.uuid4)
    document_id = Column(String if IS_SQLITE else UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON if IS_SQLITE else Vector(1536))
    page_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False, default=0, server_default="0")
    source_type = Column(String(20), nullable=False, default="site", server_default="site")
    
    document = relationship("Document")
    
    def __repr__(self):
        return f"<Chunk {self.id}>"
