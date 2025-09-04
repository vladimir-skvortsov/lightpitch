from datetime import datetime
import uuid
from typing import List

from models import Pitch, PitchCreate, PitchUpdate
from db import get_pitch_by_id, get_all_pitches, store_pitch, delete_pitch_by_id, pitch_exists


def create_pitch(pitch_data: PitchCreate) -> Pitch:
    """Create a new pitch"""
    pitch_id = str(uuid.uuid4())
    now = datetime.now()

    new_pitch = Pitch(
        id=pitch_id,
        title=pitch_data.title,
        content=pitch_data.content,
        description=pitch_data.description,
        tags=pitch_data.tags or [],
        created_at=now,
        updated_at=now,
    )

    return store_pitch(new_pitch)


def get_pitch(pitch_id: str) -> Pitch | None:
    """Get a pitch by ID"""
    return get_pitch_by_id(pitch_id)


def list_pitches() -> List[Pitch]:
    """Get all pitches"""
    return get_all_pitches()


def update_pitch(pitch_id: str, pitch_update: PitchUpdate) -> Pitch | None:
    """Update an existing pitch"""
    existing_pitch = get_pitch_by_id(pitch_id)
    if not existing_pitch:
        return None

    # Update only the fields that are provided
    update_data = pitch_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(existing_pitch, field, value)

    existing_pitch.updated_at = datetime.now()
    return store_pitch(existing_pitch)


def delete_pitch(pitch_id: str) -> Pitch | None:
    """Delete a pitch"""
    if not pitch_exists(pitch_id):
        return None

    return delete_pitch_by_id(pitch_id)
