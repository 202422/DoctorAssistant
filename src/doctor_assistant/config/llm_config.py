"""LLM configuration."""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .settings import settings

from langchain_huggingface import HuggingFaceEmbeddings



def get_llm(temperature: float = 0, model: str | None = None) -> ChatOpenAI:
    """Get configured LLM instance."""
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=model or settings.OPENAI_MODEL,
        temperature=temperature,
        base_url=settings.OPENAI_BASE_URL  # Pass base URL if set
    )



def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )