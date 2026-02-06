"""
Reading Check Routes - Thin API handlers
All business logic is delegated to core/services
"""

from fastapi import APIRouter, HTTPException, Depends
import logging

from app.api.models import (
    ReadingCheckRequest,
    ReadingCheckResponse
)
from app.core.text_processor import check_reading
from app.services.speech_provider import BaseSpeechProvider
from app.api.main import get_speech_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reading/check", response_model=ReadingCheckResponse)
async def check_reading_endpoint(
    request: ReadingCheckRequest,
    speech_provider: BaseSpeechProvider = Depends(get_speech_provider)
):
    """
    Check reading accuracy and provide feedback
    
    This is the main endpoint for reading correction.
    It accepts expected text and transcribed speech, then returns
    detailed feedback including error position and type.
    
    **Flow:**
    1. Receive expected sentence and speech transcript
    2. Detect language (or use provided)
    3. Normalize text appropriately
    4. Find errors using sequence alignment
    5. Return feedback with error details
    
    **Error Types:**
    - `success`: Read correctly
    - `skip`: Skipped a word
    - `mispronounce`: Said wrong word
    - `hesitation`: Low confidence (uncertainty)
    """
    try:
        logger.info(f"Processing reading check: language={request.language}, strict={request.strict_mode}")
        
        # Call core logic (pure Python, no I/O)
        result = check_reading(
            expected_sentence=request.expected_sentence,
            speech_transcript=request.speech_transcript,
            stt_confidence=request.stt_confidence,
            word_confidences=request.word_confidences,
            confidence_threshold=request.confidence_threshold,
            strict_mode=request.strict_mode,
            language=request.language.value if request.language else None,
            include_metadata=request.include_metadata
        )
        
        logger.info(
            f"Reading check result: correct={result['is_correct']}, "
            f"feedback={result['feedback_type']}, language={result['language']}"
        )
        
        # Convert dict to response model
        return ReadingCheckResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing reading check: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process reading check: {str(e)}"
        )


@router.post("/reading/check-batch")
async def check_reading_batch(
    requests: list[ReadingCheckRequest],
    speech_provider: BaseSpeechProvider = Depends(get_speech_provider)
):
    """
    Batch processing for multiple reading checks
    
    Useful for analyzing entire paragraphs or stories at once.
    """
    if len(requests) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 requests per batch"
        )
    
    results = []
    
    for req in requests:
        try:
            result = check_reading(
                expected_sentence=req.expected_sentence,
                speech_transcript=req.speech_transcript,
                stt_confidence=req.stt_confidence,
                word_confidences=req.word_confidences,
                confidence_threshold=req.confidence_threshold,
                strict_mode=req.strict_mode,
                language=req.language.value if req.language else None,
                include_metadata=req.include_metadata
            )
            results.append({"success": True, "result": result})
        except Exception as e:
            logger.error(f"Batch item error: {e}")
            results.append({"success": False, "error": str(e)})
    
    # Calculate aggregate stats
    total = len(results)
    correct = sum(1 for r in results if r.get("success") and r["result"]["is_correct"])
    
    return {
        "total": total,
        "correct": correct,
        "accuracy": (correct / total * 100) if total > 0 else 0,
        "results": results
    }


# Future endpoint for direct audio upload
# @router.post("/reading/transcribe-and-check")
# async def transcribe_and_check(
#     audio_file: UploadFile = File(...),
#     expected_sentence: str = Form(...),
#     language: Optional[str] = Form(None),
#     speech_provider: BaseSpeechProvider = Depends(get_speech_provider)
# ):
#     """
#     Upload audio, transcribe it, and check reading in one request
#     
#     This combines STT + correction logic for convenience
#     """
#     # Read audio data
#     audio_data = await audio_file.read()
#     
#     # Transcribe using speech provider
#     transcription = await speech_provider.transcribe(
#         audio_data=audio_data,
#         language=language,
#         expected_text=expected_sentence
#     )
#     
#     # Check reading
#     result = check_reading(
#         expected_sentence=expected_sentence,
#         speech_transcript=transcription.transcript,
#         stt_confidence=transcription.confidence,
#         word_confidences=transcription.word_confidences,
#         language=language,
#         include_metadata=True
#     )
#     
#     return {
#         "transcription": transcription,
#         "correction": result
#     }
