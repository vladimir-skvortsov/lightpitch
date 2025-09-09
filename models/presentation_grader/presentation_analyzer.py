"""
Presentation analysis using Gemini Flash for slide image analysis
"""

import base64
import io
import json
import logging
import os
import tempfile
from typing import Dict, List, Optional, Any, Tuple

import google.generativeai as genai
from PIL import Image
from PIL.Image import Image as PILImage
import fitz  # PyMuPDF for PDF processing
from pptx import Presentation

logger = logging.getLogger(__name__)


class PresentationAnalyzer:
    """
    Analyzes presentation files (PDF, PPTX) using Gemini Flash to analyze slides as images
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Google AI API key"""
        self.api_key = api_key or os.getenv('GOOGLE_AI_API_KEY')
        if not self.api_key:
            raise ValueError('Google AI API key is required. Set GOOGLE_AI_API_KEY environment variable.')

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Analysis prompts
        self.analysis_prompt = """
Проанализируй этот слайд презентации как дизайнер и эксперт по презентациям.

Оцени слайд по следующим критериям (оценка от 1 до 10):

1. **Дизайн и визуальная привлекательность**:
   - Цветовая схема и гармония
   - Типографика и читаемость шрифтов
   - Использование пространства
   - Общий визуальный баланс

2. **Структура и организация контента**:
   - Логичность структуры
   - Иерархия информации
   - Использование заголовков и подзаголовков
   - Ясность подачи материала

3. **Читаемость и восприятие**:
   - Размер и контрастность текста
   - Количество текста на слайде
   - Качество изображений и графики
   - Отсутствие визуального беспорядка

4. **Профессиональность**:
   - Соответствие корпоративному стилю
   - Качество исполнения
   - Внимание к деталям
   - Общее впечатление

Верни результат в JSON формате:
{
  "scores": {
    "design": число от 1 до 10,
    "structure": число от 1 до 10,
    "readability": число от 1 до 10,
    "professionalism": число от 1 до 10
  },
  "analysis": {
    "strengths": ["список сильных сторон"],
    "weaknesses": ["список слабых сторон"],
    "recommendations": ["список рекомендаций"]
  },
  "details": {
    "text_amount": "мало/средне/много",
    "color_scheme": "описание цветовой схемы",
    "font_readability": "хорошая/средняя/плохая",
    "visual_elements": "описание визуальных элементов"
  }
}

Будь критичным, но конструктивным. Давай конкретные рекомендации для улучшения.
"""

    def extract_slides_from_pdf(self, pdf_path: str) -> List[PILImage]:
        """Extract slides as images from PDF file"""
        slides = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Convert page to image (300 DPI for good quality)
                mat = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes('png')
                img = Image.open(io.BytesIO(img_data))
                slides.append(img)
            doc.close()
            logger.info(f'Extracted {len(slides)} slides from PDF')
            return slides
        except Exception as e:
            logger.error(f'Error extracting slides from PDF: {str(e)}')
            return []

    def extract_slides_from_pptx(self, pptx_path: str) -> List[PILImage]:
        """Extract slides as images from PPTX file"""
        slides: List[PILImage] = []
        try:
            # For PPTX, we need to convert slides to images
            # This requires more complex processing or external tools
            # For now, return empty list and use PDF conversion
            logger.warning('PPTX slide extraction not fully implemented. Convert to PDF first.')
            return slides
        except Exception as e:
            logger.error(f'Error extracting slides from PPTX: {str(e)}')
            return slides

    def image_to_base64(self, image: PILImage) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format='PNG')
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode()

    def analyze_slide_with_gemini(self, image: PILImage, slide_number: int) -> Dict[str, Any]:
        """Analyze a single slide using Gemini Flash"""
        try:
            # Convert image to base64
            buffered = io.BytesIO()
            image.save(buffered, format='PNG')
            buffered.seek(0)

            # Analyze with Gemini
            response = self.model.generate_content([f'Слайд #{slide_number}:\n{self.analysis_prompt}', image])

            # Try to parse JSON response
            response_text = response.text.strip()

            # Clean up response if it has markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            try:
                analysis = json.loads(response_text)
                analysis['slide_number'] = slide_number
                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, create a fallback structure
                logger.warning(f'Failed to parse JSON for slide {slide_number}, using fallback')
                return {
                    'slide_number': slide_number,
                    'scores': {'design': 7, 'structure': 7, 'readability': 7, 'professionalism': 7},
                    'analysis': {
                        'strengths': ['Слайд проанализирован'],
                        'weaknesses': ['Не удалось получить детальный анализ'],
                        'recommendations': ['Попробуйте повторить анализ'],
                    },
                    'details': {
                        'text_amount': 'средне',
                        'color_scheme': 'стандартная',
                        'font_readability': 'средняя',
                        'visual_elements': 'присутствуют',
                    },
                    'raw_response': response_text,
                }

        except Exception as e:
            logger.error(f'Error analyzing slide {slide_number} with Gemini: {str(e)}')
            return {
                'slide_number': slide_number,
                'scores': {'design': 5, 'structure': 5, 'readability': 5, 'professionalism': 5},
                'analysis': {
                    'strengths': [],
                    'weaknesses': [f'Ошибка анализа: {str(e)}'],
                    'recommendations': ['Проверьте качество слайда и повторите анализ'],
                },
                'details': {
                    'text_amount': 'неизвестно',
                    'color_scheme': 'неизвестна',
                    'font_readability': 'неизвестна',
                    'visual_elements': 'неизвестны',
                },
                'error': str(e),
            }

    def calculate_overall_scores(self, slide_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall presentation scores from individual slide analyses"""
        if not slide_analyses:
            return {
                'overall_score': 0,
                'category_scores': {'design': 0, 'structure': 0, 'readability': 0, 'professionalism': 0},
                'total_slides': 0,
            }

        # Calculate average scores
        total_scores = {'design': 0, 'structure': 0, 'readability': 0, 'professionalism': 0}
        valid_slides = 0

        for analysis in slide_analyses:
            if 'scores' in analysis:
                for category, score in analysis['scores'].items():
                    if isinstance(score, (int, float)):
                        total_scores[category] += float(score)
                        valid_slides += 1

        if valid_slides > 0:
            avg_scores = {category: round(total / len(slide_analyses), 1) for category, total in total_scores.items()}
            overall_score = round(sum(avg_scores.values()) / len(avg_scores), 1)
        else:
            avg_scores = {'design': 0, 'structure': 0, 'readability': 0, 'professionalism': 0}
            overall_score = 0

        return {'overall_score': overall_score, 'category_scores': avg_scores, 'total_slides': len(slide_analyses)}

    def compile_recommendations(self, slide_analyses: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Compile overall recommendations from slide analyses"""
        all_strengths = []
        all_weaknesses = []
        all_recommendations = []

        for analysis in slide_analyses:
            if 'analysis' in analysis:
                all_strengths.extend(analysis['analysis'].get('strengths', []))
                all_weaknesses.extend(analysis['analysis'].get('weaknesses', []))
                all_recommendations.extend(analysis['analysis'].get('recommendations', []))

        # Remove duplicates while preserving order
        unique_strengths = list(dict.fromkeys(all_strengths))
        unique_weaknesses = list(dict.fromkeys(all_weaknesses))
        unique_recommendations = list(dict.fromkeys(all_recommendations))

        return {
            'strengths': unique_strengths[:10],  # Limit to top 10
            'weaknesses': unique_weaknesses[:10],
            'recommendations': unique_recommendations[:10],
        }

    def analyze_presentation(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a presentation file and return comprehensive analysis

        Args:
            file_path: Path to the presentation file (PDF or PPTX)

        Returns:
            Dictionary with analysis results
        """
        logger.info(f'Starting presentation analysis for: {file_path}')

        # Determine file type and extract slides
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.pdf':
            slides = self.extract_slides_from_pdf(file_path)
        elif file_extension in ['.pptx', '.ppt']:
            slides = self.extract_slides_from_pptx(file_path)
        else:
            return {
                'error': f'Unsupported file format: {file_extension}',
                'overall_score': 0,
                'slide_analyses': [],
                'recommendations': [],
            }

        if not slides:
            return {
                'error': 'No slides could be extracted from the presentation',
                'overall_score': 0,
                'slide_analyses': [],
                'recommendations': [],
            }

        # Analyze each slide
        slide_analyses = []
        for i, slide_image in enumerate(slides, 1):
            logger.info(f'Analyzing slide {i}/{len(slides)}')
            analysis = self.analyze_slide_with_gemini(slide_image, i)
            slide_analyses.append(analysis)

        # Calculate overall scores and compile recommendations
        overall_scores = self.calculate_overall_scores(slide_analyses)
        compiled_recommendations = self.compile_recommendations(slide_analyses)

        return {
            'overall_score': overall_scores['overall_score'],
            'category_scores': overall_scores['category_scores'],
            'total_slides': overall_scores['total_slides'],
            'slide_analyses': slide_analyses,
            'strengths': compiled_recommendations['strengths'],
            'weaknesses': compiled_recommendations['weaknesses'],
            'recommendations': compiled_recommendations['recommendations'],
            'analysis_timestamp': str(int(__import__('time').time())),
        }


def analyze_presentation_file(file_path: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze a presentation file

    Args:
        file_path: Path to the presentation file
        api_key: Optional Google AI API key

    Returns:
        Analysis results dictionary
    """
    try:
        analyzer = PresentationAnalyzer(api_key=api_key)
        return analyzer.analyze_presentation(file_path)
    except Exception as e:
        logger.error(f'Presentation analysis failed: {str(e)}')
        return {
            'error': f'Analysis failed: {str(e)}',
            'overall_score': 0,
            'slide_analyses': [],
            'recommendations': [f'Ошибка анализа: {str(e)}'],
        }
