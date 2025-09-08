import uuid
from datetime import datetime
from typing import List

from db import (
    get_training_session_by_id,
    get_training_sessions_by_pitch_id,
    get_all_training_sessions,
    store_training_session,
    delete_training_session_by_id,
    training_session_exists,
)
from db_models import TrainingSession, TrainingSessionCreate, TrainingSessionUpdate


def create_training_session(session_data: TrainingSessionCreate) -> TrainingSession:
    """Create a new training session"""
    session_id = str(uuid.uuid4())
    now = datetime.now()

    new_session = TrainingSession(
        id=session_id,
        pitch_id=session_data.pitch_id,
        training_type=session_data.training_type,
        duration_seconds=session_data.duration_seconds,
        video_file_path=session_data.video_file_path,
        audio_file_path=session_data.audio_file_path,
        analysis_results=session_data.analysis_results,
        overall_score=session_data.overall_score,
        notes=session_data.notes,
        created_at=now,
        updated_at=now,
    )

    return store_training_session(new_session)


def get_training_session(session_id: str) -> TrainingSession | None:
    """Get a training session by ID"""
    return get_training_session_by_id(session_id)


def get_training_sessions_for_pitch(pitch_id: str) -> List[TrainingSession]:
    """Get all training sessions for a specific pitch"""
    sessions = get_training_sessions_by_pitch_id(pitch_id)
    # Sort by creation date (newest first)
    return sorted(sessions, key=lambda x: x.created_at, reverse=True)


def list_training_sessions() -> List[TrainingSession]:
    """Get all training sessions"""
    return get_all_training_sessions()


def update_training_session(session_id: str, session_update: TrainingSessionUpdate) -> TrainingSession | None:
    """Update an existing training session"""
    existing_session = get_training_session_by_id(session_id)
    if not existing_session:
        return None

    # Update only the fields that are provided
    update_data = session_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_session, field, value)

    existing_session.updated_at = datetime.now()
    return store_training_session(existing_session)


def delete_training_session(session_id: str) -> TrainingSession | None:
    """Delete a training session"""
    if not training_session_exists(session_id):
        return None

    return delete_training_session_by_id(session_id)


def get_training_session_stats(pitch_id: str) -> dict:
    """Get statistics for training sessions of a specific pitch"""
    sessions = get_training_sessions_by_pitch_id(pitch_id)

    if not sessions:
        return {
            'total_count': 0,
            'average_score': None,
            'best_score': None,
            'latest_session': None,
            'total_duration_minutes': 0,
        }

    # Calculate statistics
    scores = [s.overall_score for s in sessions if s.overall_score is not None]
    durations = [s.duration_seconds for s in sessions if s.duration_seconds is not None]

    # Get the latest session
    latest_session = max(sessions, key=lambda x: x.created_at)

    return {
        'total_count': len(sessions),
        'average_score': round(sum(scores) / len(scores), 2) if scores else None,
        'best_score': round(max(scores), 2) if scores else None,
        'latest_session': {
            'id': latest_session.id,
            'created_at': latest_session.created_at,
            'training_type': latest_session.training_type,
            'score': latest_session.overall_score,
            'duration_seconds': latest_session.duration_seconds,
        },
        'total_duration_minutes': round(sum(durations) / 60, 1) if durations else 0,
    }
