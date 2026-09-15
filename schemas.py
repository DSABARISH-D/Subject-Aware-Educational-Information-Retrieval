from pydantic import BaseModel, Field
import uuid
from datetime import datetime


class SubjectBase(BaseModel):
    name: str = Field(..., min_length=1)  # Required and non-empty
    description: str | None = None

class SubjectCreate(SubjectBase):
    pass

class Subject(SubjectBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    name: str

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: uuid.UUID
    subject_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    text: str

class SearchResult(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    document_name: str | None = None
    page_number: int | None = None
    chunk_index: int | None = None
    source_type: str | None = None

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    text: str

class ChatSource(BaseModel):
    id: int
    document_name: str
    document_id: str
    chunk_content: str
    relevance_score: float
    page_number: int | None = None
    source_type: str | None = None

class ChatResponse(BaseModel):
    response: str
    is_covered: bool
    sources: list[ChatSource] = []
