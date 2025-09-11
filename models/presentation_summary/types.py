"""
Type definitions for presentation summary module
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SlideContent:
    """Represents content extracted from a single slide"""
    slide_number: int
    title: Optional[str] = None
    text_content: List[str] = None
    bullet_points: List[str] = None
    speaker_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.text_content is None:
            self.text_content = []
        if self.bullet_points is None:
            self.bullet_points = []


@dataclass
class PresentationContent:
    """Represents the full content of a presentation"""
    filename: str
    total_slides: int
    slides: List[SlideContent]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisResult:
    """Represents the result of presentation analysis"""
    overall_score: float
    category_scores: Dict[str, float]
    good_practices: List[Dict[str, str]]
    warnings: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    recommendations: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]
    feedback: Optional[str] = None
    analysis_timestamp: Optional[str] = None
