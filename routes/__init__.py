from .subject import router as subject_router
from .document import router as document_router
from .search import router as search_router
from .chat import router as chat_router
from .jobs import router as jobs_router
from .documents_upload import router as documents_upload_router

__all__ = [
    "subject_router",
    "document_router",
    "search_router",
    "chat_router",
    "jobs_router",
    "documents_upload_router"
]