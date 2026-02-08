"""
OpenAI Whisper Speech Provider Implementation
Requires: openai

Installation:
    pip install openai

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key
"""

from typing import Optional, Dict, Any
import os

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

from .speech_provider import (BaseSpeechProvider, TranscriptionResult,
                              PronunciationAssessment)


class WhisperSpeechProvider(BaseSpeechProvider):
    """
    OpenAI Whisper implementation

    Features:
    - Excellent multilingual transcription (100+ languages)
    - Great Arabic support
    - Simple, reliable API
    - No Docker compatibility issues
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Whisper provider

        Config keys:
            - api_key: OpenAI API key
            - model: Whisper model (default: whisper-1)
        """
        super().__init__(config)

        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. "
                              "Install with: pip install openai")

        # Get API key from config or environment
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Provide 'api_key' in config or set OPENAI_API_KEY environment variable."
            )

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.get('model', 'whisper-1')

    async def transcribe(
            self,
            audio_data: bytes,
            language: Optional[str] = None,
            expected_text: Optional[str] = None) -> TranscriptionResult:
        """
        Transcribe audio using OpenAI Whisper

        Args:
            audio_data: Audio file bytes (WAV, MP3, etc.)
            language: Language code (e.g., 'ar', 'en')
            expected_text: Not used by Whisper, but kept for interface compatibility
        """
        import io

        # Map language codes to Whisper format
        lang_map = {'ar': 'ar', 'ar-SA': 'ar', 'en': 'en', 'en-US': 'en'}

        whisper_lang = lang_map.get(language, language) if language else None

        # Create file-like object from bytes
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.wav"  # Whisper needs a filename

        try:
            # Call Whisper API
            transcription = self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=whisper_lang,
                response_format="verbose_json"  # Get detailed response
            )

            # Extract word-level timestamps and confidence if available
            word_confidences = None
            if hasattr(transcription, 'words') and transcription.words:
                word_confidences = [
                    {
                        'word': word.word,
                        'confidence':
                        1.0  # Whisper doesn't provide word confidence
                    } for word in transcription.words
                ]

            return TranscriptionResult(
                transcript=transcription.text,
                confidence=1.0,  # Whisper doesn't provide overall confidence
                word_confidences=word_confidences,
                language=transcription.language if hasattr(
                    transcription, 'language') else whisper_lang,
                provider='whisper')

        except Exception as e:
            return TranscriptionResult(transcript="",
                                       confidence=0.0,
                                       word_confidences=None,
                                       language=whisper_lang,
                                       provider='whisper',
                                       error=f"Transcription failed: {str(e)}")

    async def assess_pronunciation(
            self,
            audio_data: bytes,
            expected_text: str,
            language: Optional[str] = None) -> PronunciationAssessment:
        """
        Whisper doesn't have built-in pronunciation assessment

        Returns a basic assessment by comparing transcription to expected text.
        For more advanced pronunciation scoring, use your text_processor logic.
        """
        # Get transcription
        result = await self.transcribe(audio_data, language, expected_text)

        if not result.transcript:
            return PronunciationAssessment(accuracy_score=0.0,
                                           fluency_score=0.0,
                                           completeness_score=0.0,
                                           phoneme_scores=None)

        # Simple accuracy based on text matching
        # Your text_processor.py already does better analysis than this!
        from difflib import SequenceMatcher

        similarity = SequenceMatcher(
            None,
            expected_text.lower().strip(),
            result.transcript.lower().strip()).ratio()

        accuracy_score = similarity * 100

        return PronunciationAssessment(
            accuracy_score=accuracy_score,
            fluency_score=accuracy_score,  # Simplified
            completeness_score=accuracy_score,  # Simplified
            phoneme_scores=None  # Not available from Whisper
        )

    def is_available(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.api_key and OPENAI_AVAILABLE)
