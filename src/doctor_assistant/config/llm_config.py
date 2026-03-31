"""
LLM Configuration Module for Doctor Assistant Multi-Agent System.

Provides factory functions for creating LLM and embedding instances
used by all agents (Planner, Supervisor, and Specialist agents).
"""

import os
import ssl

import requests
import urllib3
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings

from .settings import settings


# =============================================================================
# CORPORATE PROXY SSL BYPASS
# =============================================================================
# The corporate proxy re-signs HTTPS traffic with an internal CA not trusted
# by Python's certifi bundle. We disable SSL verification globally for all
# libraries that use requests/urllib3 (huggingface_hub, sentence-transformers).

# Suppress InsecureRequestWarning spam in logs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Tell huggingface_hub to skip SSL verification (covers hf_hub_download calls)
os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"

# Tell requests-based libraries to skip CA bundle verification
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""

# Patch the default SSL context so urllib3 stops verifying certificates
_original_create_default_context = ssl.create_default_context

def _no_verify_ssl_context(*args, **kwargs):
    ctx = _original_create_default_context(*args, **kwargs)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

ssl.create_default_context = _no_verify_ssl_context

# Patch requests.Session so every HTTP call skips SSL verification
_original_request = requests.Session.request

def _no_ssl_request(self, method, url, **kwargs):
    kwargs.setdefault("verify", False)
    return _original_request(self, method, url, **kwargs)

requests.Session.request = _no_ssl_request


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

    Note: SSL verification is disabled via module-level patches to handle
    corporate proxy environments.
    
    Returns:
        Configured HuggingFaceEmbeddings instance.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
    )