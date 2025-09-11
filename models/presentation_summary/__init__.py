"""
Presentation Summary Module

This module provides functionality to analyze presentation files (.pptx) and generate
comprehensive summaries using LLM analysis.
"""

from .presentation_summarizer import PresentationSummarizer, analyze_presentation

__all__ = ['PresentationSummarizer', 'analyze_presentation']
