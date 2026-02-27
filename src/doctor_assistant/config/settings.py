"""Application settings using dotenv."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# Find project root and load .env
def get_project_root() -> Path:
    """Find project root by looking for .env file."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    return current.parent.parent.parent.parent  # fallback


# Load .env immediately
load_dotenv(get_project_root() / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL", None)


    # Smithery MCP (renamed to NEON_SMITHERY_* in environment)
    NEON_SMITHERY_API_KEY: str = os.getenv("NEON_SMITHERY_API_KEY", "")
    NEON_SMITHERY_MCP_URL: str = os.getenv("NEON_SMITHERY_MCP_URL", "https://api.smithery.ai/connect/test_syntax/neon-CHOJ/mcp")
    # backward compatibility for old variable names (optional)
    SMITHERY_API_KEY: str = os.getenv("SMITHERY_API_KEY", NEON_SMITHERY_API_KEY)
    SMITHERY_MCP_URL: str = os.getenv("SMITHERY_MCP_URL", NEON_SMITHERY_MCP_URL)
    
    # Neon Database
    NEON_PROJECT_ID: str = os.getenv("NEON_PROJECT_ID", "")
    NEON_BRANCH_ID: str | None = os.getenv("NEON_BRANCH_ID", None)
    NEON_DATABASE_NAME: str = "neondb"

    # Google Maps
    GOOGLE_MAPS_API_KEY: str | None = os.getenv("GOOGLE_MAPS_API_KEY", None)

    # Google Maps via Smithery MCP (new vars)
    MAP_SMITHERY_API_KEY: str = os.getenv("MAP_SMITHERY_API_KEY", "")
    MAP_SMITHERY_MCP_URL: str = os.getenv("MAP_SMITHERY_MCP_URL", "")

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "doctor-assistant")

    # App settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Quick access
settings = get_settings()


# Test
if __name__ == "__main__":
    print("=" * 50)
    print("📋 DOCTOR ASSISTANT SETTINGS")
    print("=" * 50)
    
    # LLM Settings
    print("\n🤖 LLM Configuration:")
    print(f"   Provider: {settings.LLM_PROVIDER}")
    if settings.LLM_PROVIDER == "openai":
        print(f"   OpenAI Key: {settings.OPENAI_API_KEY[:10]}..." if settings.OPENAI_API_KEY else "   OpenAI Key: ❌ Not set")
        print(f"   OpenAI Model: {settings.OPENAI_MODEL}")
    else:
        print(f"   Gemini Key: {settings.GEMINI_API_KEY[:10]}..." if settings.GEMINI_API_KEY else "   Gemini Key: ❌ Not set")
        print(f"   Gemini Model: {settings.GEMINI_MODEL}")
    
    # MCP Settings
    print("\n🔌 MCP Configuration:")
    # show whichever key is actually used
    key_preview = settings.NEON_SMITHERY_API_KEY or settings.SMITHERY_API_KEY
    print(f"   Smithery Key: {key_preview[:10]}..." if key_preview else "   Smithery Key: ❌ Not set")
    print(f"   Neon Project: {settings.NEON_PROJECT_ID or '❌ Not set'}")

    # Map Smithery Settings
    print("\n🗺️ Map Smithery Configuration:")
    print(f"   Map API Key: {settings.MAP_SMITHERY_API_KEY[:10]}..." if settings.MAP_SMITHERY_API_KEY else "   Map API Key: ❌ Not set")
    print(f"   Map MCP URL: {settings.MAP_SMITHERY_MCP_URL or '❌ Not set'}")
    
    # LangSmith Settings
    print("\n📊 LangSmith Configuration:")
    print(f"   Tracing Enabled: {'✅ Yes' if settings.LANGCHAIN_TRACING_V2 else '❌ No'}")
    print(f"   Project: {settings.LANGCHAIN_PROJECT}")
    print(f"   API Key: {settings.LANGCHAIN_API_KEY[:10]}..." if settings.LANGCHAIN_API_KEY else "   API Key: ❌ Not set")
    
    # App Settings
    print("\n⚙️ App Configuration:")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   Log Level: {settings.LOG_LEVEL}")
    
    print("\n" + "=" * 50)