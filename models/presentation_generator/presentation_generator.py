"""
Presentation Generator using LLM to create improved presentations
"""

import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

# Add the project root to the path to import openai_client
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.text_editor.openai_client import OpenAIService
from .types import SlideContent, GeneratedPresentation, GenerationRequest

logger = logging.getLogger(__name__)


class PresentationGenerator:
    """
    Generates improved presentation files based on analysis results
    """
    
    def __init__(self, model: str = 'gpt-4o-mini'):
        """Initialize with OpenAI service"""
        self.openai_service = OpenAIService(model=model)
        
        # Generation prompt
        self.generation_prompt = """
Ты эксперт по созданию презентаций. Создай улучшенную версию презентации на основе анализа и найденных проблем.

АНАЛИЗ ОРИГИНАЛЬНОЙ ПРЕЗЕНТАЦИИ:
{analysis_summary}

НАЙДЕННЫЕ ПРОБЛЕМЫ:
{warnings_summary}

КРИТИЧЕСКИЕ ОШИБКИ:
{errors_summary}

РЕКОМЕНДАЦИИ:
{recommendations_summary}

ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ:
{user_requirements}

Создай улучшенную презентацию, которая:
1. Исправляет все найденные проблемы
2. Применяет все рекомендации
3. Соответствует лучшим практикам презентаций
4. Имеет четкую структуру и логику
5. Использует простой и понятный язык
6. Избегает канцеляризмов и лишних слов

Верни результат в JSON формате:
{{
  "title": "Название презентации",
  "slides": [
    {{
      "title": "Заголовок слайда",
      "content": ["основная мысль слайда"],
      "bullet_points": ["ключевые пункты"],
      "speaker_notes": "заметки для докладчика"
    }}
  ],
  "improvements_applied": [
    "список примененных улучшений"
  ],
  "theme": "modern/classic/minimal",
  "notes": "дополнительные заметки"
}}

Важные принципы:
- Один слайд = одна основная идея
- Максимум 6 пунктов на слайд
- Короткие, четкие формулировки
- Логичная последовательность
- Убедительные аргументы
"""
    
    def format_analysis_for_generation(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Format analysis data for generation prompt"""
        
        # Extract warnings
        warnings = analysis.get('warnings', [])
        warnings_text = []
        for warning in warnings:
            warnings_text.append(f"• {warning.get('title', '')}: {warning.get('description', '')}")
        
        # Extract errors
        errors = analysis.get('errors', [])
        errors_text = []
        for error in errors:
            errors_text.append(f"• {error.get('title', '')}: {error.get('description', '')}")
        
        # Extract recommendations
        recommendations = analysis.get('recommendations', [])
        
        # Extract strengths and areas for improvement
        strengths = analysis.get('strengths', [])
        areas_for_improvement = analysis.get('areas_for_improvement', [])
        
        return {
            'analysis_summary': f"""
Файл: {analysis.get('filename', 'Неизвестно')}
Общая оценка: {analysis.get('overall_score', 0)}/100
Количество слайдов: {analysis.get('total_slides', 0)}

Сильные стороны:
{chr(10).join([f"• {s}" for s in strengths])}

Области для улучшения:
{chr(10).join([f"• {a}" for a in areas_for_improvement])}
            """.strip(),
            
            'warnings_summary': '\n'.join(warnings_text) if warnings_text else "Предупреждений не найдено",
            
            'errors_summary': '\n'.join(errors_text) if errors_text else "Критических ошибок не найдено",
            
            'recommendations_summary': '\n'.join([f"• {r}" for r in recommendations]) if recommendations else "Рекомендации не предоставлены"
        }
    
    async def generate_presentation_content(self, request: GenerationRequest) -> Dict[str, Any]:
        """Generate presentation content using LLM"""
        try:
            # Format analysis for prompt
            formatted_analysis = self.format_analysis_for_generation(request.original_analysis)
            
            # Build user requirements
            user_requirements = request.user_requirements or "Без дополнительных требований"
            if request.target_audience:
                user_requirements += f"\nЦелевая аудитория: {request.target_audience}"
            if request.presentation_style:
                user_requirements += f"\nСтиль презентации: {request.presentation_style}"
            if request.focus_areas:
                user_requirements += f"\nФокусные области: {', '.join(request.focus_areas)}"
            
            # Create prompt
            prompt = self.generation_prompt.format(
                analysis_summary=formatted_analysis['analysis_summary'],
                warnings_summary=formatted_analysis['warnings_summary'],
                errors_summary=formatted_analysis['errors_summary'],
                recommendations_summary=formatted_analysis['recommendations_summary'],
                user_requirements=user_requirements
            )
            
            logger.info("Generating presentation content with LLM...")
            response_json = await self.openai_service.analyze_text(
                prompt=prompt,
                text="Создай улучшенную презентацию",
                expect_json=True
            )
            
            response = json.loads(response_json)
            
            # Validate and structure response
            if 'slides' not in response:
                raise ValueError("Generated response missing slides")
            
            # Convert to our data structures
            slides = []
            for slide_data in response['slides']:
                slide = SlideContent(
                    title=slide_data.get('title', ''),
                    content=slide_data.get('content', []),
                    bullet_points=slide_data.get('bullet_points', []),
                    speaker_notes=slide_data.get('speaker_notes')
                )
                slides.append(slide)
            
            presentation = GeneratedPresentation(
                title=response.get('title', 'Улучшенная презентация'),
                slides=slides,
                theme=response.get('theme', 'modern'),
                improvements_applied=response.get('improvements_applied', [])
            )
            
            return {
                'success': True,
                'presentation': presentation,
                'raw_response': response
            }
            
        except Exception as e:
            logger.error(f"Error generating presentation content: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'presentation': None
            }
    
    def create_pptx_file(self, presentation: GeneratedPresentation, output_path: str) -> bool:
        """Create .pptx file from generated presentation"""
        try:
            # Create new presentation
            prs = Presentation()
            
            # Set slide size to widescreen
            prs.slide_width = Inches(13.33)
            prs.slide_height = Inches(7.5)
            
            # Create slides
            for i, slide_content in enumerate(presentation.slides):
                # Add slide layout
                slide_layout = prs.slide_layouts[0]  # Title slide layout
                slide = prs.slides.add_slide(slide_layout)
                
                # Add title
                title_shape = slide.shapes.title
                title_shape.text = slide_content.title
                
                # Style title
                title_paragraph = title_shape.text_frame.paragraphs[0]
                title_paragraph.font.size = Pt(32)
                title_paragraph.font.bold = True
                title_paragraph.alignment = PP_ALIGN.CENTER
                title_paragraph.font.color.rgb = RGBColor(51, 51, 51)
                
                # Add content
                if slide_content.content or slide_content.bullet_points:
                    # Create text box for content
                    left = Inches(1)
                    top = Inches(2.5)
                    width = Inches(11.33)
                    height = Inches(4)
                    
                    textbox = slide.shapes.add_textbox(left, top, width, height)
                    text_frame = textbox.text_frame
                    text_frame.word_wrap = True
                    
                    # Add main content
                    if slide_content.content:
                        for j, content_item in enumerate(slide_content.content):
                            if j == 0:
                                p = text_frame.paragraphs[0]
                            else:
                                p = text_frame.add_paragraph()
                            
                            p.text = content_item
                            p.font.size = Pt(18)
                            p.font.color.rgb = RGBColor(68, 68, 68)
                            p.space_after = Pt(12)
                    
                    # Add bullet points
                    if slide_content.bullet_points:
                        for bullet in slide_content.bullet_points:
                            p = text_frame.add_paragraph()
                            p.text = bullet
                            p.font.size = Pt(16)
                            p.font.color.rgb = RGBColor(85, 85, 85)
                            p.level = 0
                            p.space_after = Pt(8)
                
                # Add speaker notes if available
                if slide_content.speaker_notes:
                    notes_slide = slide.notes_slide
                    notes_text_frame = notes_slide.notes_text_frame
                    notes_text_frame.text = slide_content.speaker_notes
            
            # Save presentation
            prs.save(output_path)
            logger.info(f"Presentation saved to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating PPTX file: {str(e)}")
            return False
    
    async def generate_improved_presentation(
        self, 
        analysis: Dict[str, Any], 
        output_path: str,
        user_requirements: Optional[str] = None,
        target_audience: Optional[str] = None,
        presentation_style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate and save improved presentation
        
        Args:
            analysis: Original presentation analysis results
            output_path: Path to save the new .pptx file
            user_requirements: Additional user requirements
            target_audience: Target audience description
            presentation_style: Preferred presentation style
            
        Returns:
            Dictionary with generation results
        """
        try:
            # Create generation request
            request = GenerationRequest(
                original_analysis=analysis,
                user_requirements=user_requirements,
                target_audience=target_audience,
                presentation_style=presentation_style
            )
            
            # Generate content
            generation_result = await self.generate_presentation_content(request)
            
            if not generation_result['success']:
                return {
                    'success': False,
                    'error': generation_result['error'],
                    'file_path': None
                }
            
            presentation = generation_result['presentation']
            
            # Create PPTX file
            file_created = self.create_pptx_file(presentation, output_path)
            
            if not file_created:
                return {
                    'success': False,
                    'error': 'Failed to create PPTX file',
                    'file_path': None
                }
            
            return {
                'success': True,
                'file_path': output_path,
                'presentation_title': presentation.title,
                'slides_count': len(presentation.slides),
                'improvements_applied': presentation.improvements_applied,
                'theme': presentation.theme,
                'slides_data': [
                    {
                        'title': slide.title,
                        'content': slide.content,
                        'bullet_points': slide.bullet_points,
                        'speaker_notes': slide.speaker_notes
                    }
                    for slide in presentation.slides
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in generate_improved_presentation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'file_path': None
            }


async def generate_improved_presentation(
    analysis: Dict[str, Any], 
    output_path: str,
    model: str = 'gpt-4o-mini',
    user_requirements: Optional[str] = None,
    target_audience: Optional[str] = None,
    presentation_style: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate improved presentation
    
    Args:
        analysis: Original presentation analysis results
        output_path: Path to save the new .pptx file
        model: LLM model to use
        user_requirements: Additional user requirements
        target_audience: Target audience description
        presentation_style: Preferred presentation style
        
    Returns:
        Dictionary with generation results
    """
    try:
        generator = PresentationGenerator(model=model)
        return await generator.generate_improved_presentation(
            analysis=analysis,
            output_path=output_path,
            user_requirements=user_requirements,
            target_audience=target_audience,
            presentation_style=presentation_style
        )
    except Exception as e:
        logger.error(f"Presentation generation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'file_path': None
        }
