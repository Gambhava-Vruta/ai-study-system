"""
embeddings.py — Embedding Model Configuration

Centralizes the embedding model setup so all modules use the same config.
Uses HuggingFaceEmbeddings (sentence-transformers) — runs locally, no API key needed.
"""

from langchain_huggingface import HuggingFaceEmbeddings

# Default embedding model name (small, fast, works well for RAG)
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings(model: str = DEFAULT_MODEL) -> HuggingFaceEmbeddings:
    """
    Create and return a HuggingFaceEmbeddings instance.

    Args:
        model: Name of the sentence-transformers model to use.

    Returns:
        Configured HuggingFaceEmbeddings object.
    """
    return HuggingFaceEmbeddings(model_name=model)
