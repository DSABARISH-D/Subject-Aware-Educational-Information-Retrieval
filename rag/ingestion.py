import hashlib
import os
from typing import Dict, Optional

from sqlalchemy.orm import Session

from crud.document_manager import get_documents_by_subject
from models.chunk import Chunk
from models.document import Document
from rag.document_processors import extract_document_pages
from rag.processing import get_embeddings, get_text_chunks


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ingest_file(
    db: Session,
    content: bytes,
    filename: str,
    subject_id,
    source_type: str,
    logger=None,
) -> Optional[Dict[str, int]]:
    """Ingest one file through the shared extraction, chunking, and embedding pipeline."""
    file_hash = content_sha256(content)
    existing = db.query(Document).filter(
        Document.subject_id == subject_id,
        Document.name == filename,
        Document.content_hash == file_hash,
        Document.source_type == source_type,
    ).first()
    if existing:
        return None

    pages, success, file_type = extract_document_pages(content, filename)
    if not success:
        raise ValueError(f"Failed to extract text from {filename} ({file_type})")

    page_chunks = []
    for page_number, page_text in pages:
        if not page_text.strip():
            continue
        page_chunks.extend(
            (page_number, chunk)
            for chunk in get_text_chunks(page_text)
            if chunk.strip()
        )
    if not page_chunks:
        raise ValueError(f"No text content found in {filename}")

    embeddings = get_embeddings([chunk for _, chunk in page_chunks])
    document = Document(
        name=os.path.basename(filename),
        content=content,
        subject_id=subject_id,
        content_hash=file_hash,
        source_type=source_type,
    )
    db.add(document)
    db.flush()

    for index, ((page_number, chunk_content), embedding) in enumerate(zip(page_chunks, embeddings)):
        db.add(Chunk(
            document_id=document.id,
            content=chunk_content,
            embedding=embedding,
            page_number=page_number,
            chunk_index=index,
            source_type=source_type,
        ))
    db.commit()

    result = {"document": document, "pages": len(pages), "chunks": len(page_chunks), "embeddings": len(embeddings), "inserted": len(page_chunks)}
    if logger:
        logger.info("Ingested %s: %s", filename, result)
    return result