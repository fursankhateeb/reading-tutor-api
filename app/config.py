"""
Configuration Management - Environment-based settings
Supports: Development, Testing, Production environments
"""

import os
from typing import Optional, Dict, Any
from enum import Enum


class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Config:
    """
    Base configuration class

    Loads settings from environment variables with sensible defaults
    """

    # Application
    APP_NAME: str = "Reading Tutor API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # API Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"

    # CORS
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:19006"  # React Native defaults
    ).split(",")

    # Speech Provider
    SPEECH_PROVIDER: str = os.getenv("SPEECH_PROVIDER", "mock")

    # Azure Speech Service
    AZURE_SPEECH_KEY: Optional[str] = os.getenv("AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION: Optional[str] = os.getenv("AZURE_SPEECH_REGION")
    AZURE_SPEECH_LANGUAGE: str = os.getenv("AZURE_SPEECH_LANGUAGE", "ar-SA")

    # Storage
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "memory")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Supabase
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")

    # Reading Tutor Settings
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    STRICT_MODE_DEFAULT: bool = os.getenv("STRICT_MODE_DEFAULT", "false").lower() == "true"

    # Session Management
    SESSION_TTL: int = int(os.getenv("SESSION_TTL", "3600"))  # 1 hour
    MAX_SESSION_SIZE: int = int(os.getenv("MAX_SESSION_SIZE", "1000"))  # Max sentences per session

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    @classmethod
    def get_speech_config(cls) -> Dict[str, Any]:
        """Get speech provider configuration"""
        if cls.SPEECH_PROVIDER == "azure":
            return {
                "subscription_key": cls.AZURE_SPEECH_KEY,
                "region": cls.AZURE_SPEECH_REGION,
                "language": cls.AZURE_SPEECH_LANGUAGE
            }
        elif cls.SPEECH_PROVIDER == "mock":
            return {
                "mock_transcripts": {},
                "default_transcript": ""
            }
        else:
            return {}

    @classmethod
    def get_storage_config(cls) -> Dict[str, Any]:
        """Get storage configuration"""
        if cls.STORAGE_TYPE == "redis":
            return {"redis_url": cls.REDIS_URL}
        elif cls.STORAGE_TYPE == "supabase":
            return {
                "supabase_url": cls.SUPABASE_URL,
                "supabase_key": cls.SUPABASE_KEY
            }
        else:
            return {}

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If required settings