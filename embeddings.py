"""
embeddings.py — Embedding Model Configuration

Uses HuggingFace Inference API — embeddings run on HF servers,
no local model download, no heavy RAM usage. Perfect for free cloud hosting.
"""

import os
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings

# Lightweight embedding model via HF Inference API
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings(model: str = DEFAULT_MODEL) -> HuggingFaceInferenceAPIEmbeddings:
    """
    Create and return a HuggingFaceInferenceAPIEmbeddings instance.
    Makes API calls to HuggingFace servers — no local model loading.

    Args:
        model: HuggingFace model repo name.

    Returns:
        Configured HuggingFaceInferenceAPIEmbeddings object.
    """
    api_key = os.environ.get("HUGGINGFACEHUB_API_TOKEN", "")
    return HuggingFaceInferenceAPIEmbeddings(
        api_key=api_key,
        model_name=model,
    )
