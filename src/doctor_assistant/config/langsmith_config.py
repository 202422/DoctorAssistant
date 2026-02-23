"""LangSmith configuration and setup."""

import os
from .settings import settings


def setup_langsmith() -> bool:
    """
    Setup LangSmith tracing.
    
    This function ensures all required environment variables are set
    for LangSmith to work properly with LangChain/LangGraph.
    
    Returns:
        bool: True if LangSmith tracing is enabled, False otherwise.
    """
    
    # Check if tracing is enabled
    if not settings.LANGCHAIN_TRACING_V2:
        print("ℹ️  LangSmith tracing is disabled")
        print("   Set LANGCHAIN_TRACING_V2=true in .env to enable")
        return False
    
    # Check if API key is set
    if not settings.LANGCHAIN_API_KEY:
        print("⚠️  LangSmith tracing enabled but LANGCHAIN_API_KEY is not set")
        print("   Get your API key from: https://smith.langchain.com/settings")
        return False
    
    # Set environment variables (LangChain reads these automatically)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    
    print("✅ LangSmith tracing enabled")
    print(f"   📊 Project: {settings.LANGCHAIN_PROJECT}")
    print(f"   🔗 Endpoint: {settings.LANGCHAIN_ENDPOINT}")
    print(f"   🔑 API Key: {settings.LANGCHAIN_API_KEY[:15]}...")
    print(f"   🌐 Dashboard: https://smith.langchain.com/o/default/projects/p/{settings.LANGCHAIN_PROJECT}")
    
    return True


def disable_langsmith():
    """
    Disable LangSmith tracing.
    
    Useful for testing or when you want to temporarily disable tracing.
    """
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    print("ℹ️  LangSmith tracing disabled")


def get_langsmith_status() -> dict:
    """
    Get current LangSmith configuration status.
    
    Returns:
        dict: Configuration status and details.
    """
    return {
        "enabled": settings.LANGCHAIN_TRACING_V2,
        "project": settings.LANGCHAIN_PROJECT,
        "endpoint": settings.LANGCHAIN_ENDPOINT,
        "api_key_set": bool(settings.LANGCHAIN_API_KEY),
        "api_key_preview": settings.LANGCHAIN_API_KEY[:10] + "..." if settings.LANGCHAIN_API_KEY else None
    }


# Test
if __name__ == "__main__":
    print("=" * 50)
    print("🔧 LANGSMITH CONFIGURATION TEST")
    print("=" * 50)
    
    # Show current status
    status = get_langsmith_status()
    print("\n📊 Current Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Try to setup
    print("\n🚀 Setting up LangSmith...")
    result = setup_langsmith()
    
    print(f"\n✅ Setup result: {'Success' if result else 'Failed/Disabled'}")
    print("=" * 50)