"""
FastAPI Application - Thin API Layer
All business logic is in core/services layers
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import config
from app.services.speech_provider import SpeechProviderFactory, MockSpeechProvider
from app.services.storage import StorageFactory

# Setup logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# Global instances (initialized in lifespan)
speech_provider = None
storage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    
    Initializes services on startup, cleans up on shutdown
    """
    global speech_provider, storage
    
    # Startup
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Environment: {config.ENVIRONMENT}")
    
    try:
        # Validate configuration
        config.validate()
        
        # Initialize speech provider
        logger.info(f"Initializing speech provider: {config.SPEECH_PROVIDER}")
        
        # Register mock provider (always available)
        SpeechProviderFactory.register_provider('mock', MockSpeechProvider)
        
        # TODO: Register other providers when implemented
        # from app.services.azure_speech import AzureSpeechProvider
        # SpeechProviderFactory.register_provider('azure', AzureSpeechProvider)
        
        speech_provider = SpeechProviderFactory.create_provider(
            provider_name=config.SPEECH_PROVIDER,
            config=config.get_speech_config()
        )
        
        if not speech_provider.is_available():
            logger.warning(f"Speech provider '{config.SPEECH_PROVIDER}' not properly configured")
        
        # Initialize storage
        logger.info(f"Initializing storage: {config.STORAGE_TYPE}")
        storage = StorageFactory.create_storage(
            storage_type=config.STORAGE_TYPE,
            config=config.get_storage_config()
        )
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    
    # Clean up resources
    if hasattr(storage, 'close'):
        await storage.close()
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Bilingual AI Reading Tutor API for children learning Arabic and English",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection for services
def get_speech_provider():
    """Dependency: Get speech provider instance"""
    if speech_provider is None:
        raise HTTPException(
            status_code=503,
            detail="Speech provider not initialized"
        )
    return speech_provider


def get_storage():
    """Dependency: Get storage instance"""
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage not initialized"
        )
    return storage


# Root endpoints
@app.get("/")
async def root():
    """API root - health check and info"""
    return {
        "name": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "healthy",
        "environment": config.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "check_reading": "/api/v1/reading/check",
            "sessions": "/api/v1/sessions"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for deployment monitoring
    
    Returns service status and component availability
    """
    return {
        "status": "healthy",
        "services": {
            "speech_provider": speech_provider is not None and speech_provider.is_available(),
            "storage": storage is not None
        },
        "config": {
            "speech_provider": config.SPEECH_PROVIDER,
            "storage_type": config.STORAGE_TYPE,
            "environment": config.ENVIRONMENT
        }
    }


# Import and register route blueprints
from app.api.routes import reading, sessions

app.include_router(reading.router, prefix="/api/v1", tags=["Reading"])
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )
