from typing import Dict
from models import Pitch

# In-memory storage for pitches (temporary until database is added)
pitches_db: Dict[str, Pitch] = {}


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
