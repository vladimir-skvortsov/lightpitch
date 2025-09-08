from typing import Dict, List

from db_models import Pitch, TrainingSession, HypotheticalQuestion, UserInDB

# In-memory storage (temporary until database is added)
pitches_db: Dict[str, Pitch] = {}
training_sessions_db: Dict[str, TrainingSession] = {}
hypothetical_questions_db: Dict[str, HypotheticalQuestion] = {}
users_db: Dict[str, UserInDB] = {}


# Pitch operations
def get_pitch_by_id(pitch_id: str) -> Pitch | None:
    """Get a pitch by its ID"""
    return pitches_db.get(pitch_id)


def get_all_pitches() -> list[Pitch]:
    """Get all pitches"""
    return list(pitches_db.values())


def store_pitch(pitch: Pitch) -> Pitch:
    """Store a pitch in the database"""
    pitches_db[pitch.id] = pitch
    return pitch


def delete_pitch_by_id(pitch_id: str) -> Pitch | None:
    """Delete a pitch by its ID and return the deleted pitch"""
    return pitches_db.pop(pitch_id, None)


def pitch_exists(pitch_id: str) -> bool:
    """Check if a pitch exists"""
    return pitch_id in pitches_db


# Training Session operations
def get_training_session_by_id(session_id: str) -> TrainingSession | None:
    """Get a training session by its ID"""
    return training_sessions_db.get(session_id)


def get_training_sessions_by_pitch_id(pitch_id: str) -> List[TrainingSession]:
    """Get all training sessions for a specific pitch"""
    return [session for session in training_sessions_db.values() if session.pitch_id == pitch_id]


def get_all_training_sessions() -> List[TrainingSession]:
    """Get all training sessions"""
    return list(training_sessions_db.values())


def store_training_session(session: TrainingSession) -> TrainingSession:
    """Store a training session in the database"""
    training_sessions_db[session.id] = session
    return session


def delete_training_session_by_id(session_id: str) -> TrainingSession | None:
    """Delete a training session by its ID and return the deleted session"""
    return training_sessions_db.pop(session_id, None)


def training_session_exists(session_id: str) -> bool:
    """Check if a training session exists"""
    return session_id in training_sessions_db


# Hypothetical Question operations
def get_hypothetical_question_by_id(question_id: str) -> HypotheticalQuestion | None:
    """Get a hypothetical question by its ID"""
    return hypothetical_questions_db.get(question_id)


def get_hypothetical_questions_by_pitch_id(pitch_id: str) -> List[HypotheticalQuestion]:
    """Get all hypothetical questions for a specific pitch"""
    return [question for question in hypothetical_questions_db.values() if question.pitch_id == pitch_id]


def get_all_hypothetical_questions() -> List[HypotheticalQuestion]:
    """Get all hypothetical questions"""
    return list(hypothetical_questions_db.values())


def store_hypothetical_question(question: HypotheticalQuestion) -> HypotheticalQuestion:
    """Store a hypothetical question in the database"""
    hypothetical_questions_db[question.id] = question
    return question


def delete_hypothetical_question_by_id(question_id: str) -> HypotheticalQuestion | None:
    """Delete a hypothetical question by its ID and return the deleted question"""
    return hypothetical_questions_db.pop(question_id, None)


def hypothetical_question_exists(question_id: str) -> bool:
    """Check if a hypothetical question exists"""
    return question_id in hypothetical_questions_db


# User operations
def get_user_by_id(user_id: str) -> UserInDB | None:
    """Get a user by their ID"""
    return users_db.get(user_id)


def get_user_by_email(email: str) -> UserInDB | None:
    """Get a user by their email"""
    for user in users_db.values():
        if user.email == email:
            return user
    return None


def get_all_users() -> List[UserInDB]:
    """Get all users"""
    return list(users_db.values())


def store_user(user: UserInDB) -> UserInDB:
    """Store a user in the database"""
    users_db[user.id] = user
    return user


def delete_user_by_id(user_id: str) -> UserInDB | None:
    """Delete a user by their ID and return the deleted user"""
    return users_db.pop(user_id, None)


def user_exists(user_id: str) -> bool:
    """Check if a user exists"""
    return user_id in users_db


def email_exists(email: str) -> bool:
    """Check if a user with this email exists"""
    return get_user_by_email(email) is not None
