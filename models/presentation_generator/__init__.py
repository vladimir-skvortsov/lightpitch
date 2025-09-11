"""
Presentation Generator Module

This module provides functionality to generate new presentation files (.pptx) 
based on analysis results and user requirements using LLM.
"""

from .presentation_generator import PresentationGenerator, generate_improved_presentation

__all__ = ['PresentationGenerator', 'generate_improved_presentation']
