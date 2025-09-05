from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PitchBase(BaseModel):
    title: str
    content: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    presentation_file_name: Optional[str] = None
    presentation_file_path: Optional[str] = None


class PitchCreate(PitchBase):
    pass


class PitchUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    presentation_file_name: Optional[str] = None
    presentation_file_path: Optional[str] = None


class Pitch(PitchBase):
    id: str
    created_at: datetime
    updated_at: datetime
