"""Reading Tutor API - Core Module"""

from .text_processor import (
    ReadingTutorCore,
    ArabicTextNormalizer,
    LanguageDetector,
    Language,
    FeedbackType,
    CorrectionResult,
    check_reading
)

__all__ = [
    'ReadingTutorCore',
    'ArabicTextNormalizer',
    'LanguageDetector',
    'Language',
    'FeedbackType',
    'CorrectionResult',
    'check_reading'
]
