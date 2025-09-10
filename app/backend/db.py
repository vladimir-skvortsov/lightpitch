from typing import Dict, List

from airtable_client import airtable_client
from db_models import HypotheticalQuestion, Pitch, TrainingSession, UserInDB


# Pitch operations
def get_pitch_by_id(pitch_id: str) -> Pitch | None:
    """Get a pitch by its ID"""
    return airtable_client.get_pitch_by_id(pitch_id)


def get_all_pitches() -> list[Pitch]:
    """Get all pitches"""
    return airtable_client.get_all_pitches()


def store_pitch(pitch: Pitch) -> Pitch:
    """Store a pitch in the database"""
    if pitch_exists(pitch.id):
        from db_models import PitchUpdate

        pitch_update = PitchUpdate(
            title=pitch.title,
            content=pitch.content,
            planned_duration_minutes=pitch.planned_duration_minutes,
            description=pitch.description,
            tags=pitch.tags,
            presentation_file_name=pitch.presentation_file_name,
            presentation_file_path=pitch.presentation_file_path,
        )
        updated_pitch = airtable_client.update_pitch(pitch.id, pitch_update)
        return updated_pitch if updated_pitch else pitch
    else:
        from db_models import PitchCreate

        pitch_create = PitchCreate(
            title=pitch.title,
            content=pitch.content,
            planned_duration_minutes=pitch.planned_duration_minutes,
            description=pitch.description,
            tags=pitch.tags,
            presentation_file_name=pitch.presentation_file_name,
            presentation_file_path=pitch.presentation_file_path,
        )
        return airtable_client.create_pitch(pitch_create, pitch.user_id, pitch.id)


def delete_pitch_by_id(pitch_id: str) -> Pitch | None:
    """Delete a pitch by its ID and return the deleted pitch"""
    pitch = get_pitch_by_id(pitch_id)
    if pitch and airtable_client.delete_pitch(pitch_id):
        return pitch
    return None


def pitch_exists(pitch_id: str) -> bool:
    """Check if a pitch exists"""
    return get_pitch_by_id(pitch_id) is not None


# Training Session operations
def get_training_session_by_id(session_id: str) -> TrainingSession | None:
    """Get a training session by its ID"""
    return airtable_client.get_training_session_by_id(session_id)


def get_training_sessions_by_pitch_id(pitch_id: str) -> List[TrainingSession]:
    """Get all training sessions for a specific pitch"""
    return airtable_client.get_training_sessions_by_pitch_id(pitch_id)


def get_all_training_sessions() -> List[TrainingSession]:
    """Get all training sessions"""
    return airtable_client.get_all_training_sessions()


def store_training_session(session: TrainingSession) -> TrainingSession:
    """Store a training session in the database"""
    if training_session_exists(session.id):
        from db_models import TrainingSessionUpdate

        session_update = TrainingSessionUpdate(
            duration_seconds=session.duration_seconds,
            video_file_path=session.video_file_path,
            audio_file_path=session.audio_file_path,
            analysis_results=session.analysis_results,
            overall_score=session.overall_score,
            notes=session.notes,
        )
        updated_session = airtable_client.update_training_session(session.id, session_update)
        return updated_session if updated_session else session
    else:
        from db_models import TrainingSessionCreate

        session_create = TrainingSessionCreate(
            pitch_id=session.pitch_id,
            training_type=session.training_type,
            duration_seconds=session.duration_seconds,
            video_file_path=session.video_file_path,
            audio_file_path=session.audio_file_path,
            analysis_results=session.analysis_results,
            overall_score=session.overall_score,
            notes=session.notes,
        )
        return airtable_client.create_training_session(session_create, session.id)


def delete_training_session_by_id(session_id: str) -> TrainingSession | None:
    """Delete a training session by its ID and return the deleted session"""
    session = get_training_session_by_id(session_id)
    if session and airtable_client.delete_training_session(session_id):
        return session
    return None


def training_session_exists(session_id: str) -> bool:
    """Check if a training session exists"""
    return get_training_session_by_id(session_id) is not None


# Hypothetical Question operations
def get_hypothetical_question_by_id(question_id: str) -> HypotheticalQuestion | None:
    """Get a hypothetical question by its ID"""
    return airtable_client.get_hypothetical_question_by_id(question_id)


def get_hypothetical_questions_by_pitch_id(pitch_id: str) -> List[HypotheticalQuestion]:
    """Get all hypothetical questions for a specific pitch"""
    return airtable_client.get_hypothetical_questions_by_pitch_id(pitch_id)


def get_all_hypothetical_questions() -> List[HypotheticalQuestion]:
    """Get all hypothetical questions"""
    return airtable_client.get_all_hypothetical_questions()


def store_hypothetical_question(question: HypotheticalQuestion) -> HypotheticalQuestion:
    """Store a hypothetical question in the database"""
    if hypothetical_question_exists(question.id):
        from db_models import HypotheticalQuestionUpdate

        question_update = HypotheticalQuestionUpdate(
            question_text=question.question_text,
            category=question.category,
            difficulty=question.difficulty,
            suggested_answer=question.suggested_answer,
            context=question.context,
            preparation_tips=question.preparation_tips,
        )
        updated_question = airtable_client.update_hypothetical_question(question.id, question_update)
        return updated_question if updated_question else question
    else:
        from db_models import HypotheticalQuestionCreate

        question_create = HypotheticalQuestionCreate(
            pitch_id=question.pitch_id,
            question_text=question.question_text,
            category=question.category,
            difficulty=question.difficulty,
            suggested_answer=question.suggested_answer,
            context=question.context,
            preparation_tips=question.preparation_tips,
        )
        return airtable_client.create_hypothetical_question(question_create, question.id)


def delete_hypothetical_question_by_id(question_id: str) -> HypotheticalQuestion | None:
    """Delete a hypothetical question by its ID and return the deleted question"""
    question = get_hypothetical_question_by_id(question_id)
    if question and airtable_client.delete_hypothetical_question(question_id):
        return question
    return None


def hypothetical_question_exists(question_id: str) -> bool:
    """Check if a hypothetical question exists"""
    return get_hypothetical_question_by_id(question_id) is not None


# User operations
def get_user_by_id(user_id: str) -> UserInDB | None:
    """Get a user by their ID"""
    return airtable_client.get_user_by_id(user_id)


def get_user_by_email(email: str) -> UserInDB | None:
    """Get a user by their email"""
    return airtable_client.get_user_by_email(email)


def get_all_users() -> List[UserInDB]:
    """Get all users"""
    return airtable_client.get_all_users()


def store_user(user: UserInDB) -> UserInDB:
    """Store a user in the database"""
    if user_exists(user.id):
        from db_models import UserUpdate

        user_update = UserUpdate(email=user.email, full_name=user.full_name, is_active=user.is_active)
        updated_user = airtable_client.update_user(user.id, user_update)
        return updated_user if updated_user else user
    else:
        from db_models import UserCreate

        user_create = UserCreate(
            email=user.email, full_name=user.full_name, password=user.hashed_password, is_active=user.is_active
        )
        return airtable_client.create_user(user_create, user.id)


def delete_user_by_id(user_id: str) -> UserInDB | None:
    """Delete a user by their ID and return the deleted user"""
    user = get_user_by_id(user_id)
    if user and airtable_client.delete_user(user_id):
        return user
    return None


def user_exists(user_id: str) -> bool:
    """Check if a user exists"""
    return get_user_by_id(user_id) is not None


def email_exists(email: str) -> bool:
    """Check if a user with this email exists"""
    return get_user_by_email(email) is not None
