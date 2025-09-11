"""
Type definitions for presentation generator module
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SlideContent:
    """Represents content for a single slide"""
    title: str
    content: List[str]  # Main content points
    bullet_points: Optional[List[str]] = None
    speaker_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.bullet_points is None:
            self.bullet_points = []


@dataclass
class GeneratedPresentation:
    """Represents a generated presentation"""
    title: str
    slides: List[SlideContent]
    theme: str = "modern"
    improvements_applied: List[str] = None
    
    def __post_init__(self):
        if self.improvements_applied is None:
            self.improvements_applied = []


@dataclass
class GenerationRequest:
    """Request parameters for presentation generation"""
    original_analysis: Dict[str, Any]
    user_requirements: Optional[str] = None
    target_audience: Optional[str] = None
    presentation_style: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.focus_areas is None:
            self.focus_areas = []
