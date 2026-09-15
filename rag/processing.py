from langchain.text_splitter import RecursiveCharacterTextSplitter
from google import genai
from google.genai import types
from config import settings
from typing import List


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    return chunks


def get_embeddings(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """Generate Gemini embeddings for both documents and search queries."""
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key not configured")
    if not texts:
        return []

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=settings.embedding_dimension,
            task_type=task_type,
        ),
    )
    embeddings = [list(item.values) for item in response.embeddings]
    invalid = [len(embedding) for embedding in embeddings if len(embedding) != settings.embedding_dimension]
    if invalid:
        raise ValueError(
            f"Gemini returned an unexpected embedding dimension: {invalid[0]}; "
            f"expected {settings.embedding_dimension}"
        )
    return embeddings


def get_completion(query: str, context: str) -> str:
    """Generate a grounded answer using Gemini."""
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key not configured")

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_chat_model,
        contents=f"{query}\n\nStudy material:\n{context}",
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1000),
    )
    return response.text or ""
