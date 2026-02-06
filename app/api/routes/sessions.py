"""
Session Management Routes - Story reading sessions
Uses storage abstraction for persistence
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid
import logging
from typing import Dict, Any

from app.api.models import (
    SessionStartRequest,
    SessionStartResponse,
    SentenceCheckRequest,
    SentenceCheckResponse,
    SessionSummaryResponse,
    ReadingCheckResponse
)
from app.core.text_processor import check_reading, LanguageDetector, Language
from app.services.storage import BaseStorage
from app.api.main import get_storage
from app.config import config

logger = logging.getLogger(__name__)

router = APIRouter()


async def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences (simple implementation)"""
    # Split on common sentence terminators
    import re
    sentences = re.split(r'[.!?]+', text)
    # Clean and filter empty
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


async def _get_session(session_id: str, storage: BaseStorage) -> Dict[str, Any]:
    """Get session from storage or raise 404"""
    session = await storage.get(f"session:{session_id}")
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return session


async def _update_session(session_id: str, session: Dict[str, Any], storage: BaseStorage):
    """Update session in storage"""
    await storage.set(
        f"session:{session_id}",
        session,
        ttl=config.SESSION_TTL
    )


@router.post("/sessions/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    storage: BaseStorage = Depends(get_storage)
):
    """
    Start a new reading session with a story
    
    A session tracks progress through a multi-sentence story,
    allowing the child to read one sentence at a time and
    build up their reading skills progressively.
    
    **Returns:**
    - `session_id`: Use this for subsequent sentence checks
    - `total_sentences`: How many sentences in the story
    - `first_sentence`: The first sentence to read
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Split story into sentences
        sentences = await _split_into_sentences(request.story_text)
        
        if not sentences:
            raise HTTPException(
                status_code=400,
                detail="Story must contain at least one sentence"
            )
        
        if len(sentences) > config.MAX_SESSION_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Story too long. Maximum {config.MAX_SESSION_SIZE} sentences allowed"
            )
        
        # Detect language if not provided
        if request.language:
            language = request.language.value
        else:
            detected = LanguageDetector.detect_language(request.story_text)
            language = detected.value
        
        # Create session object
        session = {
            "session_id": session_id,
            "story_text": request.story_text,
            "sentences": sentences,
            "current_index": 0,
            "language": language,
            "strict_mode": request.strict_mode,
            "errors": [],
            "total_sentences": len(sentences)
        }
        
        # Store session
        await storage.set(
            f"session:{session_id}",
            session,
            ttl=config.SESSION_TTL
        )
        
        logger.info(
            f"Started session {session_id}: "
            f"{len(sentences)} sentences, language={language}"
        )
        
        return SessionStartResponse(
            session_id=session_id,
            total_sentences=len(sentences),
            first_sentence=sentences[0],
            language=language
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start session: {str(e)}"
        )


@router.post("/sessions/{session_id}/check-sentence", response_model=SentenceCheckResponse)
async def check_sentence(
    session_id: str,
    request: SentenceCheckRequest,
    storage: BaseStorage = Depends(get_storage)
):
    """
    Check the current sentence in an active session
    
    The session tracks which sentence the child should read next.
    If they read it correctly, they advance to the next sentence.
    If not, they stay on the same sentence for retry.
    
    **Flow:**
    1. Get current sentence from session
    2. Check the reading
    3. If correct, advance to next sentence
    4. If incorrect, record error but stay on same sentence
    5. Return result with next sentence (if any)
    """
    try:
        # Get session
        session = await _get_session(session_id, storage)
        
        # Check if session is complete
        if session['current_index'] >= session['total_sentences']:
            return SentenceCheckResponse(
                result=ReadingCheckResponse(
                    is_correct=True,
                    error_index=None,
                    error_word=None,
                    feedback_type="success",
                    language=session['language']
                ),
                current_index=session['current_index'],
                next_sentence=None,
                progress=100.0,
                total_errors=len(session['errors']),
                is_complete=True
            )
        
        # Get current sentence
        current_sentence = session['sentences'][session['current_index']]
        
        # Check reading
        result = check_reading(
            expected_sentence=current_sentence,
            speech_transcript=request.speech_transcript,
            stt_confidence=request.stt_confidence,
            confidence_threshold=config.CONFIDENCE_THRESHOLD,
            strict_mode=session['strict_mode'],
            language=session['language'],
            include_metadata=False
        )
        
        # Record error if any
        if not result['is_correct']:
            session['errors'].append({
                "sentence_index": session['current_index'],
                "sentence": current_sentence,
                "feedback_type": result['feedback_type'],
                "error_word": result.get('error_word')
            })
        else:
            # Advance to next sentence only if correct
            session['current_index'] += 1
        
        # Get next sentence
        next_sentence = None
        if session['current_index'] < session['total_sentences']:
            next_sentence = session['sentences'][session['current_index']]
        
        # Calculate progress
        progress = (session['current_index'] / session['total_sentences']) * 100
        
        # Update session in storage
        await _update_session(session_id, session, storage)
        
        logger.info(
            f"Session {session_id}: sentence {session['current_index']}/{session['total_sentences']}, "
            f"correct={result['is_correct']}, errors={len(session['errors'])}"
        )
        
        return SentenceCheckResponse(
            result=ReadingCheckResponse(**result),
            current_index=session['current_index'],
            next_sentence=next_sentence,
            progress=progress,
            total_errors=len(session['errors']),
            is_complete=session['current_index'] >= session['total_sentences']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking sentence: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check sentence: {str(e)}"
        )


@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: str,
    storage: BaseStorage = Depends(get_storage)
):
    """
    Get summary of a reading session
    
    Returns statistics about the session:
    - Total sentences
    - How many completed
    - Total errors
    - Accuracy percentage
    - List of errors
    """
    try:
        session = await _get_session(session_id, storage)
        
        # Calculate accuracy
        completed = session['current_index']
        total = session['total_sentences']
        errors = len(session['errors'])
        
        # Accuracy = (sentences read correctly / sentences attempted) * 100
        accuracy = 0.0
        if completed > 0:
            accuracy = ((completed - errors) / completed) * 100
            accuracy = max(0.0, accuracy)  # Don't go negative
        
        return SessionSummaryResponse(
            session_id=session_id,
            total_sentences=total,
            completed_sentences=completed,
            total_errors=errors,
            accuracy=accuracy,
            errors=session['errors']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session summary: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    storage: BaseStorage = Depends(get_storage)
):
    """
    Delete a session
    
    Useful for cleaning up after completion or cancellation
    """
    try:
        deleted = await storage.delete(f"session:{session_id}")
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )
        
        logger.info(f"Deleted session {session_id}")
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {str(e)}"
        )
