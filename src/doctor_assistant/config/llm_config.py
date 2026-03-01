"""
LLM Configuration Module for Doctor Assistant Multi-Agent System.

Provides factory functions for creating LLM and embedding instances
used by all agents (Planner, Supervisor, and Specialist agents).
"""

from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

from .settings import settings


# =============================================================================
# LLM FACTORY
# =============================================================================

def get_llm(temperature: float = 0, model: str | None = None) -> ChatOpenAI:
    """
    Create a configured ChatOpenAI instance.
    
    Used by all agents in the system:
    - Planner agent (creates execution plans)
    - Supervisor agent (routes to specialists)
    - Specialist agents (diagnosis, pharmacy finder, etc.)
    
    Args:
        temperature: Controls randomness (0 = deterministic, 1 = creative).
                     Default 0 for consistent medical responses.
        model: OpenAI model name. Falls back to settings.OPENAI_MODEL if None.
    
    Returns:
        Configured ChatOpenAI instance ready for use.
    """
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        base_url=settings.OPENAI_BASE_URL,  # Supports custom endpoints (e.g., Azure)
    )


# =============================================================================
# EMBEDDINGS FACTORY
# =============================================================================

def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Create a HuggingFace embeddings instance.
    
    Used by RAG-based specialist agents:
    - CardiovascularDiagnosis agent
    - NeurologicalDiagnosis agent
    
    Uses sentence-transformers/all-MiniLM-L6-v2:
    - Lightweight and fast
    - Good balance of speed vs quality
    - 384-dimensional vectors
    
    Returns:
        Configured HuggingFaceEmbeddings instance.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )