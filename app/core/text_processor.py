"""
Core Reading Tutor Logic - Pure Python (No External Dependencies)
Bilingual support: English & Arabic with diacritic handling
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
from dataclasses import dataclass
from enum import Enum


class FeedbackType(Enum):
    """Clean feedback types for correction results"""
    SUCCESS = "success"
    SKIP = "skip"
    MISPRONOUNCE = "mispronounce"
    HESITATION = "hesitation"


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    ARABIC = "ar"


@dataclass
class CorrectionResult:
    """
    Correction result with clean schema
    
    Core fields (always present):
        - is_correct, error_index, error_word, feedback_type, language
    
    Optional metadata (when requested):
        - confidence_score, matched_ratio
        - diacritic_warning, warning_index, warning_word
    """
    is_correct: bool
    error_index: Optional[int]
    error_word: Optional[str]
    feedback_type: str
    language: str
    
    # Optional metadata
    confidence_score: Optional[float] = None
    matched_ratio: Optional[float] = None
    
    # Diacritic warnings (Arabic lenient mode)
    diacritic_warning: bool = False
    warning_index: Optional[int] = None
    warning_word: Optional[str] = None
    
    def to_dict(self, include_metadata: bool = False) -> Dict:
        """Convert to dictionary with optional metadata"""
        data = {
            "is_correct": self.is_correct,
            "error_index": self.error_index,
            "error_word": self.error_word,
            "feedback_type": self.feedback_type,
            "language": self.language
        }
        
        if include_metadata:
            if self.confidence_score is not None:
                data["confidence_score"] = self.confidence_score
            if self.matched_ratio is not None:
                data["matched_ratio"] = self.matched_ratio
            
            if self.diacritic_warning:
                data["diacritic_warning"] = True
                if self.warning_index is not None:
                    data["warning_index"] = self.warning_index
                if self.warning_word is not None:
                    data["warning_word"] = self.warning_word
        
        return data


class ArabicTextNormalizer:
    """
    Arabic text normalization with Unicode-robust diacritic handling
    """
    
    # Character normalization mappings
    NORMALIZATION_MAP = {
        # Alif variants -> base Alif
        'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا',
        # Ta Marbuta -> Ha
        'ة': 'ه',
        # Alif Maqsura -> Ya
        'ى': 'ي',
        # Hamza variants
        'ؤ': 'و', 'ئ': 'ي',
    }
    
    # Configurable isolated Hamza normalization
    NORMALIZE_ISOLATED_HAMZA = True
    
    @classmethod
    def remove_diacritics(cls, text: str) -> str:
        """
        Remove Arabic diacritics using Unicode categories
        
        Uses NFKD decomposition + filtering Mn category (non-spacing marks)
        This is robust and catches ALL Unicode diacritics
        """
        if not text:
            return ""
        
        # Remove Tatweel (stretching character)
        text = text.replace('\u0640', '')
        
        # Decompose to separate base chars from combining marks
        decomposed = unicodedata.normalize("NFKD", text)
        
        # Filter out non-spacing marks (diacritics)
        no_marks = "".join(
            ch for ch in decomposed 
            if unicodedata.category(ch) != "Mn"
        )
        
        # Recompose to canonical form
        return unicodedata.normalize("NFC", no_marks)
    
    @classmethod
    def normalize_arabic(cls, text: str, remove_diacritics: bool = True,
                         normalize_hamza: bool = None) -> str:
        """
        Comprehensive Arabic normalization for comparison
        
        Args:
            text: Input Arabic text
            remove_diacritics: Whether to strip diacritics
            normalize_hamza: Override for isolated Hamza (ء) removal
        """
        if not text:
            return ""
        
        # Remove Tatweel
        text = text.replace('\u0640', '')
        
        # Remove diacritics
        if remove_diacritics:
            text = cls.remove_diacritics(text)
        
        # Apply character normalization
        for old_char, new_char in cls.NORMALIZATION_MAP.items():
            text = text.replace(old_char, new_char)
        
        # Optional isolated Hamza removal
        use_hamza_norm = normalize_hamza if normalize_hamza is not None else cls.NORMALIZE_ISOLATED_HAMZA
        if use_hamza_norm:
            text = text.replace('ء', '')
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text
    
    @classmethod
    def has_diacritics(cls, text: str) -> bool:
        """Check if text contains diacritics"""
        if not text:
            return False
        decomposed = unicodedata.normalize("NFKD", text)
        return any(unicodedata.category(ch) == "Mn" for ch in decomposed)
    
    @classmethod
    def compare_with_diacritics(cls, text1: str, text2: str) -> Tuple[bool, bool]:
        """
        Compare texts with and without diacritics
        
        Returns:
            (exact_match, base_match_without_diacritics)
        """
        exact_match = text1 == text2
        base_match = cls.remove_diacritics(text1) == cls.remove_diacritics(text2)
        return exact_match, base_match


class LanguageDetector:
    """Detect language from text"""
    
    @staticmethod
    def detect_language(text: str) -> Language:
        """
        Detect if text is Arabic or English
        
        If any Arabic characters present, consider it Arabic
        """
        if not text:
            return Language.ENGLISH
        
        # Arabic Unicode range: \u0600-\u06FF
        arabic_pattern = r'[\u0600-\u06FF]'
        
        if re.search(arabic_pattern, text):
            return Language.ARABIC
        
        return Language.ENGLISH


class ReadingTutorCore:
    """
    Core reading correction logic - Pure Python, no I/O
    
    Detects: skips, mispronunciations, hesitations
    Handles: Arabic diacritics, RTL text, bilingual support
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.7,
        similarity_threshold: float = 0.8,
        strict_mode: bool = False
    ):
        """
        Args:
            confidence_threshold: Minimum STT confidence (0.0-1.0)
            similarity_threshold: Minimum word similarity for match
            strict_mode: Enforce Arabic diacritics in comparison
        """
        self.confidence_threshold = confidence_threshold
        self.similarity_threshold = similarity_threshold
        self.strict_mode = strict_mode
        self.normalizer = ArabicTextNormalizer()
    
    def process_reading(
        self,
        expected_sentence: str,
        speech_transcript: str,
        stt_confidence: Optional[float] = None,
        word_confidences: Optional[List[float]] = None,
        language_override: Optional[str] = None,
        include_metadata: bool = False
    ) -> CorrectionResult:
        """
        Main entry point for reading correction
        
        Args:
            expected_sentence: Correct text
            speech_transcript: What child said (from STT)
            stt_confidence: Overall STT confidence score
            word_confidences: Per-word confidence scores
            language_override: Force language detection ('en' or 'ar')
            include_metadata: Include optional fields in result
        
        Returns:
            CorrectionResult with error detection and feedback
        """
        # Detect language
        if language_override:
            language = Language.ARABIC if language_override == 'ar' else Language.ENGLISH
        else:
            language = LanguageDetector.detect_language(expected_sentence)
        
        # Check for hesitation (low confidence)
        if stt_confidence is not None and stt_confidence < self.confidence_threshold:
            return CorrectionResult(
                is_correct=False,
                error_index=None,
                error_word=None,
                feedback_type=FeedbackType.HESITATION.value,
                language=language.value,
                confidence_score=stt_confidence if include_metadata else None,
                matched_ratio=None
            )
        
        # Handle empty transcript
        if not speech_transcript.strip():
            return CorrectionResult(
                is_correct=False,
                error_index=None,
                error_word=None,
                feedback_type=FeedbackType.HESITATION.value,
                language=language.value,
                confidence_score=stt_confidence if include_metadata else None,
                matched_ratio=None
            )
        
        # Perform correction based on language
        if language == Language.ARABIC:
            result = self._check_arabic_reading(
                expected_sentence,
                speech_transcript,
                word_confidences
            )
        else:
            result = self._check_english_reading(
                expected_sentence,
                speech_transcript,
                word_confidences
            )
        
        # Add metadata if requested
        if include_metadata:
            result.confidence_score = stt_confidence
        
        return result
    
    def _check_english_reading(
        self,
        expected: str,
        spoken: str,
        word_confidences: Optional[List[float]] = None
    ) -> CorrectionResult:
        """Check English reading with sequence alignment"""
        
        # Normalize for comparison
        expected_normalized = expected.lower().strip()
        spoken_normalized = spoken.lower().strip()
        
        # Remove punctuation for comparison
        expected_clean = re.sub(r'[^\w\s]', '', expected_normalized)
        spoken_clean = re.sub(r'[^\w\s]', '', spoken_normalized)
        
        expected_words = expected_clean.split()
        spoken_words = spoken_clean.split()
        expected_words_original = expected.split()
        
        # Check for perfect match
        if expected_clean == spoken_clean:
            return CorrectionResult(
                is_correct=True,
                error_index=None,
                error_word=None,
                feedback_type=FeedbackType.SUCCESS.value,
                language=Language.ENGLISH.value,
                matched_ratio=1.0
            )
        
        # Use sequence matching to find errors
        error_index, error_word, feedback_type = self._align_and_find_error(
            expected_words,
            spoken_words,
            expected_words_original,
            word_confidences,
            Language.ENGLISH
        )
        
        # Calculate match ratio
        matcher = SequenceMatcher(None, expected_words, spoken_words)
        match_ratio = matcher.ratio()
        
        return CorrectionResult(
            is_correct=False,
            error_index=error_index,
            error_word=error_word,
            feedback_type=feedback_type,
            language=Language.ENGLISH.value,
            matched_ratio=match_ratio
        )
    
    def _check_arabic_reading(
        self,
        expected: str,
        spoken: str,
        word_confidences: Optional[List[float]] = None
    ) -> CorrectionResult:
        """Check Arabic reading with diacritic handling"""
        
        # Normalize for comparison
        expected_normalized = self.normalizer.normalize_arabic(
            expected,
            remove_diacritics=True
        )
        spoken_normalized = self.normalizer.normalize_arabic(
            spoken,
            remove_diacritics=True
        )
        
        expected_words_normalized = expected_normalized.split()
        spoken_words_normalized = spoken_normalized.split()
        expected_words_original = expected.split()
        spoken_words_original = spoken.split()
        
        # Check for base match (without diacritics)
        if expected_normalized == spoken_normalized:
            # In strict mode, check diacritics
            if self.strict_mode:
                has_diacritic_mismatch = False
                first_mismatch_index = None
                
                for idx, (exp_word, spoken_word) in enumerate(
                    zip(expected_words_original, spoken_words_original)
                ):
                    if idx >= len(expected_words_original) or idx >= len(spoken_words_original):
                        break
                    
                    exact_match, base_match = self.normalizer.compare_with_diacritics(
                        exp_word, spoken_word
                    )
                    
                    if base_match and not exact_match:
                        has_diacritic_mismatch = True
                        if first_mismatch_index is None:
                            first_mismatch_index = idx
                
                if has_diacritic_mismatch:
                    return CorrectionResult(
                        is_correct=False,
                        error_index=first_mismatch_index,
                        error_word=expected_words_original[first_mismatch_index] if first_mismatch_index is not None else None,
                        feedback_type=FeedbackType.MISPRONOUNCE.value,
                        language=Language.ARABIC.value,
                        matched_ratio=1.0,
                        diacritic_warning=True,
                        warning_index=first_mismatch_index,
                        warning_word=expected_words_original[first_mismatch_index] if first_mismatch_index is not None else None
                    )
            
            # Lenient mode or no diacritic issues
            return CorrectionResult(
                is_correct=True,
                error_index=None,
                error_word=None,
                feedback_type=FeedbackType.SUCCESS.value,
                language=Language.ARABIC.value,
                matched_ratio=1.0
            )
        
        # Find errors using sequence alignment
        error_index, error_word, feedback_type = self._align_and_find_error(
            expected_words_normalized,
            spoken_words_normalized,
            expected_words_original,
            word_confidences,
            Language.ARABIC
        )
        
        # Calculate match ratio
        matcher = SequenceMatcher(None, expected_words_normalized, spoken_words_normalized)
        match_ratio = matcher.ratio()
        
        return CorrectionResult(
            is_correct=False,
            error_index=error_index,
            error_word=error_word,
            feedback_type=feedback_type,
            language=Language.ARABIC.value,
            matched_ratio=match_ratio
        )
    
    def _align_and_find_error(
        self,
        expected_words: List[str],
        spoken_words: List[str],
        expected_words_original: List[str],
        word_confidences: Optional[List[float]],
        language: Language
    ) -> Tuple[Optional[int], Optional[str], str]:
        """
        Align sequences and find first error
        
        Returns:
            (error_index, error_word, feedback_type)
        """
        matcher = SequenceMatcher(None, expected_words, spoken_words)
        opcodes = matcher.get_opcodes()
        
        def get_display_word(index: int, word_list: List[str], original_list: List[str]) -> str:
            """Get word as it appears in original text (with diacritics for Arabic)"""
            if language == Language.ARABIC and original_list:
                if index < len(original_list):
                    return original_list[index]
            if index < len(word_list):
                return word_list[index]
            return ""
        
        # Find first error in alignment
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'delete':
                # Word was skipped
                display_word = get_display_word(i1, expected_words, expected_words_original)
                return i1, display_word, FeedbackType.SKIP.value
            
            elif tag == 'replace':
                # Word was mispronounced
                # Check for word-level hesitation first
                if word_confidences and j1 < len(word_confidences):
                    if word_confidences[j1] < self.confidence_threshold:
                        display_word = get_display_word(i1, expected_words, expected_words_original)
                        return i1, display_word, FeedbackType.HESITATION.value
                
                display_word = get_display_word(i1, expected_words, expected_words_original)
                return i1, display_word, FeedbackType.MISPRONOUNCE.value
            
            elif tag == 'insert':
                # Extra word (treat as mispronunciation of expected sequence)
                if i1 < len(expected_words):
                    display_word = get_display_word(i1, expected_words, expected_words_original)
                    return i1, display_word, FeedbackType.MISPRONOUNCE.value
        
        # No error found (shouldn't reach here if called correctly)
        return None, None, FeedbackType.SUCCESS.value


# Convenience function for simple usage
def check_reading(
    expected_sentence: str,
    speech_transcript: str,
    stt_confidence: Optional[float] = None,
    word_confidences: Optional[List[float]] = None,
    confidence_threshold: float = 0.7,
    strict_mode: bool = False,
    language: Optional[str] = None,
    include_metadata: bool = False
) -> Dict:
    """
    Convenience function for quick reading checks
    
    Returns dict instead of CorrectionResult for easy JSON serialization
    """
    tutor = ReadingTutorCore(
        confidence_threshold=confidence_threshold,
        similarity_threshold=0.8,
        strict_mode=strict_mode
    )
    
    result = tutor.process_reading(
        expected_sentence=expected_sentence,
        speech_transcript=speech_transcript,
        stt_confidence=stt_confidence,
        word_confidences=word_confidences,
        language_override=language,
        include_metadata=include_metadata
    )
    
    return result.to_dict(include_metadata=include_metadata)
