"""
Settings Module for Doctor Assistant Multi-Agent System.

Loads configuration from environment variables using dotenv.
Provides centralized access to API keys and service configurations.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

def get_project_root() -> Path:
    """
    Find the project root directory by searching for .env file.
    
    Traverses up from this file's location until .env is found.
    Falls back to 4 levels up if .env doesn't exist.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".env").exists():
            return parent
    # Fallback: assume standard project structure
    return current.parent.parent.parent.parent


# Load environment variables at module import
load_dotenv(get_project_root() / ".env")


# =============================================================================
# SETTINGS CLASS
# =============================================================================

class Settings:
    """
    Centralized configuration for the Doctor Assistant system.
    
    All settings are loaded from environment variables with sensible defaults.
    Organized by service/feature for easy maintenance.
    """

    # -------------------------------------------------------------------------
    # OpenAI Configuration (for LLM agents)
    # -------------------------------------------------------------------------
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL", None)  # Custom endpoint if needed

    # -------------------------------------------------------------------------
    # Neon Database MCP (for PatientDataRetriever agent)
    # -------------------------------------------------------------------------
    NEON_SMITHERY_API_KEY: str = os.getenv("NEON_SMITHERY_API_KEY", "")
    NEON_SMITHERY_MCP_URL: str = os.getenv(
        "NEON_SMITHERY_MCP_URL",
        "https://api.smithery.ai/connect/test_syntax/neon-CHOJ/mcp"
    )
    # Legacy variable names (backward compatibility)
    SMITHERY_API_KEY: str = os.getenv("SMITHERY_API_KEY", NEON_SMITHERY_API_KEY)
    SMITHERY_MCP_URL: str = os.getenv("SMITHERY_MCP_URL", NEON_SMITHERY_MCP_URL)

    # Neon project identifiers
    NEON_PROJECT_ID: str = os.getenv("NEON_PROJECT_ID", "")
    NEON_BRANCH_ID: str | None = os.getenv("NEON_BRANCH_ID", None)
    NEON_DATABASE_NAME: str = "neondb"

    # -------------------------------------------------------------------------
    # Google Maps MCP (for PharmacyFinder agent)
    # -------------------------------------------------------------------------
    GOOGLE_MAPS_API_KEY: str | None = os.getenv("GOOGLE_MAPS_API_KEY", None)
    MAP_SMITHERY_API_KEY: str = os.getenv("MAP_SMITHERY_API_KEY", "")
    MAP_SMITHERY_MCP_URL: str = os.getenv("MAP_SMITHERY_MCP_URL", "")

    # -------------------------------------------------------------------------
    # LangSmith (tracing & observability)
    # -------------------------------------------------------------------------
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "doctor-assistant")

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# =============================================================================
# SETTINGS ACCESS
# =============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached Settings instance (singleton pattern).
    
    Uses lru_cache to ensure only one Settings object exists.
    """
    return Settings()


# Global settings instance for convenient imports
settings = get_settings()


# =============================================================================
# CONFIGURATION VERIFICATION (run directly to test)
# =============================================================================

if __name__ == "__main__":
    """Print all settings to verify configuration is loaded correctly."""
    
    print("=" * 50)
    print("📋 DOCTOR ASSISTANT SETTINGS")
    print("=" * 50)

    # Helper to safely preview API keys
    def preview_key(key: str) -> str:
        return f"{key[:10]}..." if key else "❌ Not set"

    # LLM
    print("\n🤖 LLM Configuration:")
    print(f"   OpenAI Key: {preview_key(settings.OPENAI_API_KEY)}")

    # Neon MCP
    print("\n🔌 Neon MCP Configuration:")
    print(f"   Smithery Key: {preview_key(settings.NEON_SMITHERY_API_KEY)}")
    print(f"   Neon Project: {settings.NEON_PROJECT_ID or '❌ Not set'}")

    # Google Maps MCP
    print("\n🗺️ Google Maps MCP Configuration:")
    print(f"   Map API Key: {preview_key(settings.MAP_SMITHERY_API_KEY)}")
    print(f"   Map MCP URL: {settings.MAP_SMITHERY_MCP_URL or '❌ Not set'}")

    # LangSmith
    print("\n📊 LangSmith Configuration:")
    print(f"   Tracing: {'✅ Enabled' if settings.LANGCHAIN_TRACING_V2 else '❌ Disabled'}")
    print(f"   Project: {settings.LANGCHAIN_PROJECT}")
    print(f"   API Key: {preview_key(settings.LANGCHAIN_API_KEY)}")

    # App
    print("\n⚙️ App Configuration:")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   Log Level: {settings.LOG_LEVEL}")

    print("\n" + "=" * 50)