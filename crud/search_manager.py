from sqlalchemy.orm import Session
from sqlalchemy import text
from models.chunk import Chunk
from models.document import Document
from rag.processing import get_embeddings
from database import IS_SQLITE
import uuid
import math


def search_chunks(db: Session, subject_id: uuid.UUID, query: str, top_k: int = 10):
    """
    Search for chunks belonging ONLY to the specified subject.
    Filtering by subject occurs BEFORE similarity ordering/ranking.
    Supports both PostgreSQL (pgvector) and SQLite fallback.
    """
    query_embedding = get_embeddings([query], task_type="RETRIEVAL_QUERY")[0]
    subject_str = str(subject_id)
    
    if not IS_SQLITE:
        sql_query = text("""
                 SELECT c.id, c.document_id, c.content, c.embedding,
                     c.page_number, c.chunk_index, c.source_type, d.name AS document_name,
                     c.embedding <=> :query_embedding AS distance
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.subject_id = :subject_id
            ORDER BY distance ASC
            LIMIT :top_k
        """)
        
        result = db.execute(sql_query, {
            'query_embedding': str(query_embedding),
            'subject_id': subject_str, 
            'top_k': top_k
        })
        
        chunks = []
        for row in result:
            chunk = Chunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                embedding=row.embedding,
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                source_type=row.source_type,
            )
            chunk.distance = row.distance
            chunk.document_name = row.document_name
            chunks.append(chunk)
        return chunks
    else:
        chunks_db = db.query(Chunk).join(Document).filter(Document.subject_id == subject_str).all()
        if not chunks_db:
            return []
        
        scored_chunks = []
        for chunk in chunks_db:
            emb = chunk.embedding
            if isinstance(emb, str):
                import json
                emb = json.loads(emb)
            if not emb:
                continue
            
            dot_product = sum(a * b for a, b in zip(query_embedding, emb))
            norm_a = math.sqrt(sum(a * a for a in query_embedding))
            norm_b = math.sqrt(sum(b * b for b in emb))
            sim = dot_product / (norm_a * norm_b) if (norm_a and norm_b) else 0.0
            distance = 1.0 - sim
            
            chunk.distance = distance
            scored_chunks.append((chunk, distance))
        
        scored_chunks.sort(key=lambda x: x[1])
        return [c for c, _ in scored_chunks[:top_k]]
