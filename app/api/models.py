"""
API Models - Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from enum import Enum


class LanguageCode(str, Enum):
    """Supported language codes"""
    ENGLISH = "en"
    ARABIC = "ar"


class FeedbackTypeResponse(str, Enum):
    """Feedback type for responses"""
    SUCCESS = "success"
    SKIP = "skip"
    MISPRONOUNCE = "mispronounce"
    HESITATION = "hesitation"


# ========== Reading Check Models ==========

class ReadingCheckRequest(BaseModel):
    """Request model for reading check endpoint"""
    
    expected_sentence: str = Field(
        ...,
        description="The correct text the child should read",
        min_length=1,
        max_length=1000
    )
    
    speech_transcript: str = Field(
        ...,
        description="What the STT system transcribed from the child's reading",
        max_length=1000
    )
    
    stt_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Overall STT confidence score (0.0-1.0)"
    )
    
    word_confidences: Optional[List[float]] = Field(
        None,
        description="Per-word confidence scores from STT"
    )
    
    language: Optional[LanguageCode] = Field(
        None,
        description="Force language detection (en or ar)"
    )
    
    strict_mode: bool = Field(
        False,
        description="Enable strict diacritic checking for Arabic"
    )
    
    confidence_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for hesitation detection"
    )
    
    include_metadata: bool = Field(
        False,
        description="Include additional metadata in response"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "expected_sentence": "The cat sat on the mat",
                "speech_transcript": "The cat sat on the hat",
                "stt_confidence": 0.85,
                "language": "en",
                "strict_mode": False,
                "confidence_threshold": 0.7,
                "include_metadata": False
            }
        }


class ReadingCheckResponse(BaseModel):
    """Response model for reading check"""
    
    is_correct: bool = Field(
        ...,
        description="Whether the reading was correct"
    )
    
    error_index: Optional[int] = Field(
        None,
        description="Index of the first error word (if any)"
    )
    
    error_word: Optional[str] = Field(
        None,
        description="The word that was read incorrectly or skipped"
    )
    
    feedback_type: FeedbackTypeResponse = Field(
        ...,
        description="Type of feedback (success, skip, mispronounce, hesitation)"
    )
    
    language: LanguageCode = Field(
        ...,
        description="Detected or specified language"
    )
    
    # Optional metadata fields
    confidence_score: Optional[float] = Field(
        None,
        description="STT confidence score (if metadata included)"
    )
    
    matched_ratio: Optional[float] = Field(
        None,
        description="Text similarity ratio (if metadata included)"
    )
    
    diacritic_warning: Optional[bool] = Field(
        None,
        description="Whether diacritics were missing (Arabic lenient mode)"
    )
    
    warning_index: Optional[int] = Field(
        None,
        description="Index of word with diacritic warning"
    )
    
    warning_word: Optional[str] = Field(
        None,
        description="Word with diacritic warning"
    )


# ========== Session Models ==========

class SessionStartRequest(BaseModel):
    """Request to start a new reading session"""
    
    story_text: str = Field(
        ...,
        description="Full text of the story to read",
        min_length=1,
        max_length=10000
    )
    
    language: Optional[LanguageCode] = Field(
        None,
        description="Language of the story (auto-detected if not provided)"
    )
    
    strict_mode: bool = Field(
        False,
        description="Enable strict mode for this session"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "story_text": "The cat sat on the mat. It was a sunny day. The cat was happy.",
                "language": "en",
                "strict_mode": False
            }
        }


class SessionStartResponse(BaseModel):
    """Response when starting a new session"""
    
    session_id: str = Field(
        ...,
        description="Unique session identifier"
    )
    
    total_sentences: int = Field(
        ...,
        description="Total number of sentences in the story"
    )
    
    first_sentence: str = Field(
        ...,
        description="The first sentence to read"
    )
    
    language: LanguageCode = Field(
        ...,
        description="Detected language"
    )


class SentenceCheckRequest(BaseModel):
    """Request to check a sentence in an active session"""
    
    speech_transcript: str = Field(
        ...,
        description="What the child said",
        max_length=1000
    )
    
    stt_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="STT confidence score"
    )


class SentenceCheckResponse(BaseModel):
    """Response for sentence check in session"""
    
    result: ReadingCheckResponse = Field(
        ...,
        description="Reading check result"
    )
    
    current_index: int = Field(
        ...,
        description="Current sentence index"
    )
    
    next_sentence: Optional[str] = Field(
        None,
        description="Next sentence to read (if any)"
    )
    
    progress: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Progress percentage"
    )
    
    total_errors: int = Field(
        ...,
        description="Total errors in session so far"
    )
    
    is_complete: bool = Field(
        ...,
        description="Whether the story is complete"
    )


class SessionSummaryResponse(BaseModel):
    """Summary of a reading session"""
    
    session_id: str
    total_sentences: int
    completed_sentences: int
    total_errors: int
    accuracy: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall accuracy percentage"
    )
    errors: List[Dict[str, Any]] = Field(
        ...,
        description="List of errors that occurred"
    )


# ========== Audio Upload Models (for future use) ==========

class AudioTranscriptionRequest(BaseModel):
    """Request for audio transcription"""
    
    language: Optional[LanguageCode] = Field(
        None,
        description="Expected language (for STT optimization)"
    )
    
    expected_text: Optional[str] = Field(
        None,
        description="Expected text (for pronunciation assessment)"
    )


class AudioTranscriptionResponse(BaseModel):
    """Response from audio transcription"""
    
    transcript: str = Field(
        ...,
        description="Transcribed text"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score"
    )
    
    word_confidences: Optional[List[float]] = Field(
        None,
        description="Per-word confidence scores"
    )
    
    language: str = Field(
        ...,
        description="Detected language"
    )
