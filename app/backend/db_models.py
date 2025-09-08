from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, field_validator, EmailStr


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


# Training Session Models
class TrainingType(str, Enum):
    VIDEO_UPLOAD = 'video_upload'
    VIDEO_RECORD = 'video_record'
    AUDIO_ONLY = 'audio_only'


class TrainingSessionBase(BaseModel):
    pitch_id: str
    training_type: TrainingType
    duration_seconds: Optional[float] = None
    video_file_path: Optional[str] = None
    audio_file_path: Optional[str] = None
    analysis_results: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    notes: Optional[str] = None


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionUpdate(BaseModel):
    duration_seconds: Optional[float] = None
    video_file_path: Optional[str] = None
    audio_file_path: Optional[str] = None
    analysis_results: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    notes: Optional[str] = None


class TrainingSession(TrainingSessionBase):
    id: str
    created_at: datetime
    updated_at: datetime


# Hypothetical Questions Models
class QuestionCategory(str, Enum):
    BUSINESS = 'business'
    TECHNICAL = 'technical'
    PERSONAL = 'personal'
    STRATEGY = 'strategy'
    FINANCE = 'finance'
    PRODUCT = 'product'
    MARKET = 'market'
    TEAM = 'team'


class QuestionDifficulty(str, Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'


class HypotheticalQuestionBase(BaseModel):
    pitch_id: str
    question_text: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    suggested_answer: Optional[str] = None
    context: Optional[str] = None
    preparation_tips: Optional[List[str]] = []


class HypotheticalQuestionCreate(HypotheticalQuestionBase):
    pass


class HypotheticalQuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    category: Optional[QuestionCategory] = None
    difficulty: Optional[QuestionDifficulty] = None
    suggested_answer: Optional[str] = None
    context: Optional[str] = None
    preparation_tips: Optional[List[str]] = None


class HypotheticalQuestion(HypotheticalQuestionBase):
    id: str
    created_at: datetime
    updated_at: datetime


# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    hashed_password: str


# Authentication Models
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
