import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from db import delete_pitch_by_id, get_all_pitches, get_pitch_by_id, pitch_exists, store_pitch
from db_models import Pitch, PitchCreate, PitchUpdate

from models.description_generator.description_generator import DescriptionGenerator

description_generator = DescriptionGenerator()


def create_pitch(pitch_data: PitchCreate) -> Pitch:
    """Create a new pitch"""
    pitch_id = str(uuid.uuid4())
    now = datetime.now()

    if not pitch_data.description:
        pitch_data.description = description_generator.generate_description(
            title=pitch_data.title,
            speech_text=pitch_data.content,
            presentation_text=None,
        )

    new_pitch = Pitch(
        id=pitch_id,
        title=pitch_data.title,
        content=pitch_data.content or '',
        planned_duration_minutes=pitch_data.planned_duration_minutes,
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
