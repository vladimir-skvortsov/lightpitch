"""
Type definitions for presentation generator module
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class VisualElementType(Enum):
    """Types of visual elements that can be suggested"""
    CHART = "chart"
    GRAPH = "graph"
    DIAGRAM = "diagram"
    IMAGE = "image"
    TABLE = "table"
    ICON = "icon"
    INFOGRAFIC = "infografic"
    TIMELINE = "timeline"
    FLOWCHART = "flowchart"


class ChartType(Enum):
    """Types of charts"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    COLUMN = "column"
    AREA = "area"
    SCATTER = "scatter"


@dataclass
class VisualElement:
    """Represents a suggested visual element"""
    element_type: VisualElementType
    title: str
    description: str
    purpose: str
    data_suggestion: Optional[List[str]] = None
    chart_type: Optional[ChartType] = None
    position_suggestion: str = "center"
    size_suggestion: str = "medium"
    
    def __post_init__(self):
        if self.data_suggestion is None:
            self.data_suggestion = []


@dataclass
class ImprovedSlide:
    """Represents an improved slide with corrected content"""
    slide_number: int
    title: str
    content: List[str]
    bullet_points: List[str]
    speaker_notes: Optional[str] = None
    improvements_applied: List[str] = None
    suggested_visuals: List[VisualElement] = None
    
    def __post_init__(self):
        if self.improvements_applied is None:
            self.improvements_applied = []
        if self.suggested_visuals is None:
            self.suggested_visuals = []


@dataclass
class ImprovedPresentation:
    """Represents the improved presentation"""
    original_filename: str
    improved_filename: str
    total_slides: int
    slides: List[ImprovedSlide]
    improvements_summary: List[str]
    generation_timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.generation_timestamp is None:
            import time
            self.generation_timestamp = str(int(time.time()))
