"""
LangSmith Configuration Module for Doctor Assistant Multi-Agent System.

Handles setup and management of LangSmith tracing for observability.
LangSmith tracks all LLM calls, agent executions, and graph traversals.

Dashboard: https://smith.langchain.com
"""

import os
from .settings import settings


# =============================================================================
# LANGSMITH SETUP
# =============================================================================

def setup_langsmith() -> bool:
    """
    Initialize LangSmith tracing for the multi-agent system.
    
    Sets required environment variables that LangChain/LangGraph
    automatically read to enable tracing of:
    - Planner and Supervisor agent decisions
    - Specialist agent LLM calls
    - RAG retrieval operations
    - Full graph execution flow
    
    Returns:
        True if tracing is enabled and configured, False otherwise.
    """
    # Check if tracing is enabled in settings
    if not settings.LANGCHAIN_TRACING_V2:
        print("ℹ️  LangSmith tracing is disabled")
        print("   Set LANGCHAIN_TRACING_V2=true in .env to enable")
        return False

    # Validate API key exists
    if not settings.LANGCHAIN_API_KEY:
        print("⚠️  LangSmith tracing enabled but LANGCHAIN_API_KEY is not set")
        print("   Get your API key from: https://smith.langchain.com/settings")
        return False

    # Export environment variables (LangChain reads these automatically)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

    # Confirmation output
    print("✅ LangSmith tracing enabled")
    print(f"   📊 Project: {settings.LANGCHAIN_PROJECT}")
    print(f"   🔗 Endpoint: {settings.LANGCHAIN_ENDPOINT}")
    print(f"   🔑 API Key: {settings.LANGCHAIN_API_KEY[:15]}...")
    print(f"   🌐 Dashboard: https://smith.langchain.com/o/default/projects/p/{settings.LANGCHAIN_PROJECT}")

    return True


# =============================================================================
# LANGSMITH CONTROL
# =============================================================================

def disable_langsmith() -> None:
    """
    Disable LangSmith tracing at runtime.
    
    Useful for:
    - Local testing without logging
    - Reducing latency in production
    - Privacy-sensitive operations
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    print("ℹ️  LangSmith tracing disabled")


def get_langsmith_status() -> dict:
    """
    Get current LangSmith configuration status.
    
    Returns:
        Dictionary containing:
        - enabled: Whether tracing is on
        - project: Project name for grouping traces
        - endpoint: LangSmith API endpoint
        - api_key_set: Whether API key is configured
        - api_key_preview: Masked preview of API key
    """
    return {
        "enabled": settings.LANGCHAIN_TRACING_V2,
        "project": settings.LANGCHAIN_PROJECT,
        "endpoint": settings.LANGCHAIN_ENDPOINT,
        "api_key_set": bool(settings.LANGCHAIN_API_KEY),
        "api_key_preview": f"{settings.LANGCHAIN_API_KEY[:10]}..." if settings.LANGCHAIN_API_KEY else None,
    }


# =============================================================================
# CONFIGURATION TEST (run directly to verify setup)
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🔧 LANGSMITH CONFIGURATION TEST")
    print("=" * 50)

    # Display current status
    print("\n📊 Current Status:")
    status = get_langsmith_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    # Attempt setup
    print("\n🚀 Setting up LangSmith...")
    result = setup_langsmith()

    # Report result
    print(f"\n{'✅ Setup successful' if result else '❌ Setup failed or disabled'}")
    print("=" * 50)