from sqlalchemy.orm import Session
from crud.search_manager import search_chunks
from rag.processing import get_completion
from rag.reranking import hybrid_search_and_rerank
from models.subject import Subject
from typing import Dict
import uuid
import json


def get_chat_response(db: Session, subject_id: uuid.UUID, query: str, use_reranking: bool = True) -> Dict:
    """
    Get chat response with source attribution and an explicit boolean coverage flag.
    Returns a dictionary with response, is_covered, and sources.
    """
    subject = db.query(Subject).filter(Subject.id == str(subject_id)).first()
    subject_name = subject.name if subject else str(subject_id)

    # Retrieval is already subject-filtered in SQL; reranking preserves that set.
    if use_reranking:
        chunks = hybrid_search_and_rerank(db, subject_id, query, initial_k=50, final_k=10)
    else:
        chunks = search_chunks(db, subject_id, query, top_k=10)
    
    if not chunks:
        return {
            "response": "The uploaded material for this subject does not contain information to answer your question.",
            "is_covered": False,
            "sources": []
        }
    
    # Prepare context with chunk references
    context_parts = []
    sources = []
    
    for i, chunk in enumerate(chunks):
        context_parts.append(f"[Source {i+1}]: {chunk.content}")
        
        # Get document name for source attribution
        from models.document import Document
        from database import IS_SQLITE
        doc_id_val = str(chunk.document_id) if IS_SQLITE else chunk.document_id
        document = db.query(Document).filter(Document.id == doc_id_val).first()
        document_name = getattr(chunk, "document_name", None) or (document.name if document else f"Document {chunk.document_id}")
        
        # Determine relevance score based on available information
        if hasattr(chunk, 'rerank_score'):
            relevance_score = chunk.rerank_score / 10.0  # Normalize to 0-1
        elif hasattr(chunk, 'distance'):
            relevance_score = 1.0 - chunk.distance  # Distance-based score
        else:
            relevance_score = 1.0 - (i * 0.1)  # Position-based fallback
        
        sources.append({
            "id": i + 1,
            "document_name": document_name,
            "document_id": str(chunk.document_id),
            "chunk_content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            "relevance_score": max(0.0, min(1.0, relevance_score)),
            "page_number": getattr(chunk, "page_number", None),
            "source_type": getattr(chunk, "source_type", None),
        })
    
    context = "\n\n".join(context_parts)
    
    # Prompt LLM for structured JSON response with is_covered flag
    enhanced_query = f"""
You are an educational assistant.

Selected subject:
{subject_name}

Answer the question ONLY using the provided subject material context below.

Analyze whether the provided context contains sufficient information to answer the question.
Return your response strictly as a JSON object with the following schema:
{{
  "is_covered": true or false,
  "response": "Your detailed answer based strictly on the context with [Source X] citations, OR if is_covered is false, state clearly that the uploaded subject material does not cover this question."
}}

Question: {query}

Study material:
{context}

Respond ONLY with valid JSON.
"""
    
    response_text = get_completion(enhanced_query, "")
    
    is_covered = False
    final_response = response_text
    
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        
        data = json.loads(cleaned)
        if isinstance(data, dict):
            is_covered = bool(data.get("is_covered", False))
            final_response = data.get("response", response_text)
    except Exception:
        # Fallback if parsing fails
        lower_resp = response_text.lower()
        is_covered = not any(phrase in lower_resp for phrase in ["not cover", "doesn't cover", "does not cover", "insufficient information", "cannot answer"])
        final_response = response_text
    
    return {
        "response": final_response,
        "is_covered": is_covered,
        "sources": sources
    }
