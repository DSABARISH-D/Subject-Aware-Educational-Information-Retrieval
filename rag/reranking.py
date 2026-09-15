from typing import List


def llm_rerank_chunks(query: str, chunks: List, top_k: int = 10) -> List:
    """
    Rerank chunks using LLM-based relevance scoring.
    """
    if not chunks:
        return []
    
    # If we have fewer chunks than top_k, return all
    if len(chunks) <= top_k:
        return chunks
    
    return chunks[:top_k]


def hybrid_search_and_rerank(db_session, subject_id: str, query: str, 
                           initial_k: int = 50, final_k: int = 10) -> List:
    """
    Perform hybrid search: vector similarity + LLM reranking for a specific subject.
    
    1. Retrieve initial_k chunks belonging to the subject using vector similarity
    2. Rerank using LLM to select final_k chunks
    """
    from crud.search_manager import search_chunks
    
    # Step 1: Get more chunks than we need using vector similarity
    initial_chunks = search_chunks(db_session, subject_id, query, top_k=initial_k)
    
    if not initial_chunks:
        return []
    
    # Step 2: Rerank using LLM
    reranked_chunks = llm_rerank_chunks(query, initial_chunks, top_k=final_k)
    
    return reranked_chunks