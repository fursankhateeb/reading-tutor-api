"""
Speech Provider Interface - Abstract base for swappable STT services
Supports: Azure Speech, OpenAI Whisper, NVIDIA Riva, Google Cloud, etc.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SpeechProvider(Enum):
    """Available speech recognition providers"""
    AZURE = "azure"
    WHISPER = "whisper"
    RIVA = "riva"
    GOOGLE = "google"
    MOCK = "mock"  # For testing


@dataclass
class TranscriptionResult:
    """Standardized transcription result from any provider"""
    transcript: str
    confidence: float
    word_confidences: Optional[List[float]] = None
    language: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class PronunciationAssessment:
    """Pronunciation assessment result (if provider supports it)"""
    accuracy_score: float  # 0.0-1.0
    fluency_score: Optional[float] = None
    completeness_score: Optional[float] = None
    phoneme_scores: Optional[List[Dict[str, Any]]] = None


class BaseSpeechProvider(ABC):
    """
    Abstract base class for speech recognition providers
    
    All providers must implement this interface to be swappable
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration
        
        Args:
            config: Provider-specific configuration
                   (API keys, regions, model names, etc.)
        """
        self.config = config
    
    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        expected_text: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            language: Language code (e.g., 'en-US', 'ar-SA')
            expected_text: Expected text for pronunciation assessment
        
        Returns:
            TranscriptionResult with transcript and confidence
        """
        pass
    
    @abstractmethod
    async def assess_pronunciation(
        self,
        audio_data: bytes,
        expected_text: str,
        language: Optional[str] = None
    ) -> PronunciationAssessment:
        """
        Assess pronunciation quality (if supported)
        
        Args:
            audio_data: Raw audio bytes
            expected_text: Reference text
            language: Language code
        
        Returns:
            PronunciationAssessment with scores
        
        Raises:
            NotImplementedError: If provider doesn't support assessment
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is properly configured and available
        
        Returns:
            True if provider can be used
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get provider name for logging/debugging"""
        return self.__class__.__name__


class MockSpeechProvider(BaseSpeechProvider):
    """
    Mock provider for testing without actual STT service
    
    Returns predefined transcripts based on test cases
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_transcripts = config.get('mock_transcripts', {})
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        expected_text: Optional[str] = None
    ) -> TranscriptionResult:
        """Return mock transcript"""
        
        # Use expected_text as key for mock transcript
        if expected_text and expected_text in self.mock_transcripts:
            transcript = self.mock_transcripts[expected_text]
        else:
            # Default mock: return empty or predefined
            transcript = self.config.get('default_transcript', '')
        
        return TranscriptionResult(
            transcript=transcript,
            confidence=0.85,
            word_confidences=None,
            language=language,
            provider='mock'
        )
    
    async def assess_pronunciation(
        self,
        audio_data: bytes,
        expected_text: str,
        language: Optional[str] = None
    ) -> PronunciationAssessment:
        """Return mock pronunciation assessment"""
        return PronunciationAssessment(
            accuracy_score=0.90,
            fluency_score=0.85,
            completeness_score=0.95,
            phoneme_scores=None
        )
    
    def is_available(self) -> bool:
        """Mock provider is always available"""
        return True


class SpeechProviderFactory:
    """
    Factory for creating speech providers
    
    Allows runtime selection of provider based on config
    """
    
    _providers: Dict[str, type] = {
        SpeechProvider.MOCK.value: MockSpeechProvider,
        # Other providers registered at runtime
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new provider implementation
        
        Args:
            name: Provider identifier (e.g., 'azure', 'whisper')
            provider_class: Class implementing BaseSpeechProvider
        """
        if not issubclass(provider_class, BaseSpeechProvider):
            raise ValueError(f"{provider_class} must inherit from BaseSpeechProvider")
        
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        config: Dict[str, Any]
    ) -> BaseSpeechProvider:
        """
        Create a speech provider instance
        
        Args:
            provider_name: Name of provider ('azure', 'whisper', etc.)
            config: Provider-specific configuration
        
        Returns:
            Initialized provider instance
        
        Raises:
            ValueError: If provider not registered
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of registered provider names"""
        return list(cls._providers.keys())


# Example usage:
"""
# In your config/setup:
from services.azure_speech import AzureSpeechProvider
from services.whisper_speech import WhisperSpeechProvider

SpeechProviderFactory.register_provider('azure', AzureSpeechProvider)
SpeechProviderFactory.register_provider('whisper', WhisperSpeechProvider)

# In your application:
provider = SpeechProviderFactory.create_provider(
    provider_name='azure',
    config={
        'subscription_key': os.getenv('AZURE_SPEECH_KEY'),
        'region': os.getenv('AZURE_SPEECH_REGION')
    }
)

result = await provider.transcribe(audio_data, language='ar-SA')
"""
