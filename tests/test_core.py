"""
Basic Test Suite - Verify Architecture
"""

import pytest
from app.core.text_processor import (
    ReadingTutorCore,
    check_reading,
    ArabicTextNormalizer,
    LanguageDetector,
    Language
)


class TestCoreLogic:
    """Test pure core logic (no I/O)"""
    
    def test_english_perfect_match(self):
        """Test perfect English reading"""
        result = check_reading(
            expected_sentence="The cat sat on the mat",
            speech_transcript="The cat sat on the mat",
            stt_confidence=0.95
        )
        
        assert result['is_correct'] == True
        assert result['feedback_type'] == 'success'
        assert result['language'] == 'en'
    
    def test_english_mispronunciation(self):
        """Test English word mispronunciation"""
        result = check_reading(
            expected_sentence="The cat sat on the mat",
            speech_transcript="The cat sat on the hat",
            stt_confidence=0.85
        )
        
        assert result['is_correct'] == False
        assert result['feedback_type'] == 'mispronounce'
        assert result['error_word'] == 'mat'
    
    def test_english_skip(self):
        """Test skipped word"""
        result = check_reading(
            expected_sentence="The cat sat on the mat",
            speech_transcript="The cat on the mat",
            stt_confidence=0.90
        )
        
        assert result['is_correct'] == False
        assert result['feedback_type'] == 'skip'
        assert result['error_word'] == 'sat'
    
    def test_low_confidence_hesitation(self):
        """Test hesitation detection from low confidence"""
        result = check_reading(
            expected_sentence="The cat sat",
            speech_transcript="The cat sat",
            stt_confidence=0.55,
            confidence_threshold=0.7
        )
        
        assert result['is_correct'] == False
        assert result['feedback_type'] == 'hesitation'
    
    def test_arabic_without_diacritics_lenient(self):
        """Test Arabic reading without diacritics in lenient mode"""
        result = check_reading(
            expected_sentence="القِطَّةُ تَلْعَبُ",
            speech_transcript="القطة تلعب",
            stt_confidence=0.90,
            strict_mode=False
        )
        
        # Should be success in lenient mode
        assert result['feedback_type'] == 'success'
        assert result['language'] == 'ar'
    
    def test_arabic_without_diacritics_strict(self):
        """Test Arabic reading without diacritics in strict mode"""
        result = check_reading(
            expected_sentence="القِطَّةُ تَلْعَبُ",
            speech_transcript="القطة تلعب",
            stt_confidence=0.90,
            strict_mode=True
        )
        
        # Should fail in strict mode
        assert result['is_correct'] == False
    
    def test_arabic_mispronunciation(self):
        """Test Arabic word mispronunciation"""
        result = check_reading(
            expected_sentence="الكتاب على الطاولة",
            speech_transcript="الكتاب على الكرسي",
            stt_confidence=0.88
        )
        
        assert result['is_correct'] == False
        assert result['feedback_type'] == 'mispronounce'
        assert result['error_word'] == 'الطاولة'


class TestArabicNormalizer:
    """Test Arabic text normalization"""
    
    def test_remove_diacritics(self):
        """Test diacritic removal"""
        text_with = "القِطَّةُ"
        text_without = "القطة"
        
        result = ArabicTextNormalizer.remove_diacritics(text_with)
        assert result == text_without
    
    def test_has_diacritics(self):
        """Test diacritic detection"""
        assert ArabicTextNormalizer.has_diacritics("القِطَّةُ") == True
        assert ArabicTextNormalizer.has_diacritics("القطة") == False
    
    def test_character_normalization(self):
        """Test Hamza and Alif normalization"""
        text = "أإآة"
        normalized = ArabicTextNormalizer.normalize_arabic(text)
        
        # Should normalize to basic forms
        assert "ا" in normalized
        assert "ه" in normalized


class TestLanguageDetector:
    """Test language detection"""
    
    def test_detect_arabic(self):
        """Test Arabic detection"""
        lang = LanguageDetector.detect_language("مرحبا")
        assert lang == Language.ARABIC
    
    def test_detect_english(self):
        """Test English detection"""
        lang = LanguageDetector.detect_language("Hello world")
        assert lang == Language.ENGLISH
    
    def test_detect_mixed(self):
        """Test mixed text (should detect Arabic if present)"""
        lang = LanguageDetector.detect_language("Hello مرحبا")
        assert lang == Language.ARABIC


class TestMetadata:
    """Test optional metadata inclusion"""
    
    def test_metadata_included(self):
        """Test that metadata is included when requested"""
        result = check_reading(
            expected_sentence="The cat sat",
            speech_transcript="The cat sat",
            stt_confidence=0.95,
            include_metadata=True
        )
        
        assert 'confidence_score' in result
        assert 'matched_ratio' in result
        assert result['confidence_score'] == 0.95
    
    def test_metadata_excluded(self):
        """Test that metadata is excluded by default"""
        result = check_reading(
            expected_sentence="The cat sat",
            speech_transcript="The cat sat",
            stt_confidence=0.95,
            include_metadata=False
        )
        
        # Core fields should be present
        assert 'is_correct' in result
        assert 'feedback_type' in result
        
        # Optional metadata should not be present
        assert result.get('confidence_score') is None


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_transcript(self):
        """Test empty speech transcript"""
        result = check_reading(
            expected_sentence="The cat sat",
            speech_transcript="",
            stt_confidence=0.85
        )
        
        assert result['is_correct'] == False
        assert result['feedback_type'] == 'hesitation'
    
    def test_punctuation_handling(self):
        """Test that punctuation doesn't cause errors"""
        result = check_reading(
            expected_sentence="Hello, world! How are you?",
            speech_transcript="Hello world How are you",
            stt_confidence=0.90
        )
        
        # Should match despite punctuation differences
        assert result['is_correct'] == True or result['matched_ratio'] > 0.9
    
    def test_case_insensitive_english(self):
        """Test case insensitivity for English"""
        result = check_reading(
            expected_sentence="The Cat Sat On The Mat",
            speech_transcript="the cat sat on the mat",
            stt_confidence=0.95
        )
        
        assert result['is_correct'] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
