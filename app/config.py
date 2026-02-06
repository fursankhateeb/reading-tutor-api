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
            ValueError: If required settings are missing
        """
        # Validate speech provider
        if cls.SPEECH_PROVIDER == "azure":
            if not cls.AZURE_SPEECH_KEY or not cls.AZURE_SPEECH_REGION:
                raise ValueError(
                    "Azure Speech credentials missing. "
                    "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables."
                )
        
        # Validate storage
        if cls.STORAGE_TYPE == "redis" and not cls.REDIS_URL:
            raise ValueError(
                "Redis URL missing. Set REDIS_URL environment variable."
            )
        
        if cls.STORAGE_TYPE == "supabase":
            if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
                raise ValueError(
                    "Supabase credentials missing. "
                    "Set SUPABASE_URL and SUPABASE_KEY environment variables."
                )
        
        return True
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.ENVIRONMENT == Environment.PRODUCTION.value
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development"""
        return cls.ENVIRONMENT == Environment.DEVELOPMENT.value


class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    RELOAD = True
    STORAGE_TYPE = "memory"
    SPEECH_PROVIDER = "mock"


class TestingConfig(Config):
    """Testing-specific configuration"""
    ENVIRONMENT = "testing"
    STORAGE_TYPE = "memory"
    SPEECH_PROVIDER = "mock"


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    RELOAD = False
    ENVIRONMENT = "production"
    
    @classmethod
    def validate(cls) -> bool:
        """Additional production validation"""
        super().validate()
        
        # In production, don't use in-memory storage
        if cls.STORAGE_TYPE == "memory":
            raise ValueError(
                "In-memory storage not allowed in production. "
                "Use 'redis' or 'supabase'."
            )
        
        # In production, use real speech provider
        if cls.SPEECH_PROVIDER == "mock":
            raise ValueError(
                "Mock speech provider not allowed in production. "
                "Configure 'azure', 'whisper', or other real provider."
            )
        
        return True


def get_config() -> Config:
    """
    Get configuration based on environment
    
    Returns:
        Appropriate config class instance
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()


# Singleton config instance
config = get_config()


# Example usage:
"""
# In your code:
from app.config import config

# Access settings
print(config.APP_NAME)
print(config.SPEECH_PROVIDER)

# Get provider configs
speech_config = config.get_speech_config()
storage_config = config.get_storage_config()

# Validate before starting app
config.validate()
"""
