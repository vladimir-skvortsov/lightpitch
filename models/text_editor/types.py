from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TextStyle(str, Enum):
    CASUAL = 'casual'
    PROFESSIONAL = 'professional'
    SCIENTIFIC = 'scientific'


class AnalysisType(str, Enum):
    WEAK_SPOTS = 'weak_spots'
    SPEECH_TIME = 'speech_time'
    REMOVE_PARASITES = 'remove_parasites'
    REMOVE_BUREAUCRACY = 'remove_bureaucracy'
    REMOVE_PASSIVE = 'remove_passive'
    STRUCTURE_BLOCKS = 'structure_blocks'
    STYLE_TRANSFORM = 'style_transform'


class WeakSpot(BaseModel):
    position: int
    length: Optional[int] = None
    original_text: str
    issue_type: str
    explanation: Optional[str] = None
    suggestion: str
    severity: str


class ProcessingStep(BaseModel):
    step_name: str
    input_text: str
    output_text: str
    changes_made: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description='Text to analyze')
    analysis_types: List[AnalysisType] = Field(..., description='Types of analysis to perform')
    style: Optional[TextStyle] = Field(None, description='Style for transformation')
    language: str = Field('ru', description='Language code (ru, en, etc.)')


class TextAnalysisResponse(BaseModel):
    request_id: str
    original_text: str
    final_edited_text: str
    processing_steps: List[ProcessingStep]
    analysis_summary: Dict[str, Any]
    processing_time_seconds: float
    timestamp: datetime


class TextRecommendationsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    language: str = Field('ru', description='Language code')


class TextRecommendationsResponse(BaseModel):
    request_id: str
    weak_spots: List[WeakSpot]
    global_recommendations: List[str]
    processing_time_seconds: float
    timestamp: datetime


@dataclass
class AnalysisState:
    original_text: str
    current_text: str
    analysis_types: List[AnalysisType]
    style: Optional[TextStyle]
    language: str
    processing_steps: List[ProcessingStep]
    weak_spots: List[WeakSpot]
    speech_time_minutes: Optional[float] = None
    final_speech_time_minutes: Optional[float] = None
    word_count: int = 0
    final_word_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
