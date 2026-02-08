"""
Speech Provider Interface and Factory
Abstract base class for speech-to-text providers
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class FeedbackType(Enum):
    """Types of reading feedback"""
    SUCCESS = "success"
    SKIP = "skip"
    MISPRONOUNCE = "mispronounce"
    HESITATION = "hesitation"


@dataclass
class TranscriptionResult:
    """Result from speech transcription"""
    transcript: str
    confidence: float
    word_confidences: Optional[List[Dict[str, Any]]] = None
    language: Optional[str] = None
    provider: str = "unknown"
    error: Optional[str] = None


@dataclass
class PronunciationAssessment:
    """Pronunciation assessment result"""
    accuracy_score: float
    fluency_score: float
    completeness_score: float
    phoneme_scores: Optional[List[Dict[str, Any]]] = None


class BaseSpeechProvider(ABC):
    """
    Abstract base class for speech providers

    All speech providers must implement these methods
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration"""
        self.config = config

    @abstractmethod
    async def transcribe(
            self,
            audio_data: bytes,
            language: Optional[str] = None,
            expected_text: Optional[str] = None) -> TranscriptionResult:
        """
        Transcribe audio to text

        Args:
            audio_data: Audio file bytes
            language: Language code (e.g., 'ar-SA', 'en-US')
            expected_text: Expected text for pronunciation assessment (optional)

        Returns:
            TranscriptionResult with transcript and confidence
        """
        pass

    @abstractmethod
    async def assess_pronunciation(
            self,
            audio_data: bytes,
            expected_text: str,
            language: Optional[str] = None) -> PronunciationAssessment:
        """
        Assess pronunciation quality

        Args:
            audio_data: Audio file bytes
            expected_text: Reference text
            language: Language code

        Returns:
            PronunciationAssessment with scores
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is properly configured"""
        pass


class MockSpeechProvider(BaseSpeechProvider):
    """
    Mock speech provider for testing
    Returns predefined transcripts
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_transcripts = config.get('mock_transcripts', {})
        self.default_transcript = config.get('default_transcript', '')

    async def transcribe(
            self,
            audio_data: bytes,
            language: Optional[str] = None,
            expected_text: Optional[str] = None) -> TranscriptionResult:
        """Return mock transcript"""
        transcript = self.mock_transcripts.get(
            expected_text, self.default_transcript or expected_text or "")

        return TranscriptionResult(transcript=transcript,
                                   confidence=0.95,
                                   word_confidences=None,
                                   language=language or 'en',
                                   provider='mock')

    async def assess_pronunciation(
            self,
            audio_data: bytes,
            expected_text: str,
            language: Optional[str] = None) -> PronunciationAssessment:
        """Return mock assessment"""
        return PronunciationAssessment(accuracy_score=85.0,
                                       fluency_score=80.0,
                                       completeness_score=90.0,
                                       phoneme_scores=None)

    def is_available(self) -> bool:
        """Mock provider is always available"""
        return True


class SpeechProviderFactory:
    """
    Factory for creating speech providers
    """


@staticmethod
def create_provider(provider_type: str,
                    config: Dict[str, Any]) -> BaseSpeechProvider:
    """Create a speech provider instance"""
    if provider_type == "whisper":
        from .whisper_speech import WhisperSpeechProvider
        return WhisperSpeechProvider(config)
    elif provider_type == "mock":
        return MockSpeechProvider(config)
    else:
        raise ValueError(f"Unknown speech provider: {provider_type}. "
                         f"Available providers: whisper, mock")
