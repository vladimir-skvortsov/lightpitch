from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class PitchBase(BaseModel):
    title: str
    content: str
    planned_duration_minutes: int
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    presentation_file_name: Optional[str] = None
    presentation_file_path: Optional[str] = None

    @field_validator('planned_duration_minutes')
    def validate_duration(cls, v):
        if v is None:
            raise ValueError('Планируемая длительность обязательна')
        if not isinstance(v, int) or v <= 0 or v > 480:
            raise ValueError('Длительность должна быть от 1 до 480 минут')
        return v


class PitchCreate(PitchBase):
    pass


class PitchUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    planned_duration_minutes: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    presentation_file_name: Optional[str] = None
    presentation_file_path: Optional[str] = None


class Pitch(PitchBase):
    id: str
    created_at: datetime
    updated_at: datetime
