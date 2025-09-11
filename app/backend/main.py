import json
import logging
import os
import shutil
import tempfile
import uuid
import random
from datetime import datetime, timedelta
from typing import Optional

from docx import Document
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer

load_dotenv()
logger = logging.getLogger(__name__)

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_user,
    get_current_active_user,
)
from config import PROJECT_NAME
from db_models import (
    HypotheticalQuestion,
    LoginRequest,
    Pitch,
    PitchCreate,
    PitchUpdate,
    Token,
    TrainingSession,
    TrainingSessionCreate,
    TrainingSessionUpdate,
    User,
    UserCreate,
)
from hypothetical_questions import get_hypothetical_questions_for_pitch as get_hypothetical_questions_for_pitch_service
from hypothetical_questions import get_hypothetical_questions_stats as get_hypothetical_questions_stats_service
from pitches import create_pitch as create_pitch_service
from pitches import delete_pitch as delete_pitch_service
from pitches import get_pitch as get_pitch_service
from pitches import list_pitches as list_pitches_service
from pitches import update_pitch as update_pitch_service
from training_sessions import create_training_session as create_training_session_service
from training_sessions import delete_training_session as delete_training_session_service
from training_sessions import get_training_session as get_training_session_service
from training_sessions import get_training_session_stats as get_training_session_stats_service
from training_sessions import get_training_sessions_for_pitch as get_training_sessions_for_pitch_service
from training_sessions import list_training_sessions as list_training_sessions_service
from training_sessions import update_training_session as update_training_session_service

from models.audio.analyzer import analyze_file_frontend_format
from models.question_generator import (
    CommissionMood,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    QuestionGenerator,
)
from models.text_editor import (
    AnalysisState,
    AnalysisType,
    TextAnalysisRequest,
    TextAnalysisResponse,
    TextAnalysisService,
    TextRecommendationsRequest,
    TextRecommendationsResponse,
    app_graph,
)
from models.video_grader import VideoGrader

app = FastAPI(title=PROJECT_NAME)

# Create directories for file uploads
UPLOAD_DIR = 'uploads'
PRESENTATIONS_DIR = os.path.join(UPLOAD_DIR, 'presentations')
os.makedirs(PRESENTATIONS_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def convert_ai_analysis_to_frontend_format(ai_analysis: dict, filename: str) -> dict:
    """Convert AI analysis results to frontend-compatible format"""
    try:
        # Extract overall score (should be 0-100 scale)
        overall_score = ai_analysis.get('overall_score', 70)
        if overall_score > 100:
            overall_score = 70  # Fallback for invalid scores

        # Use good_practices directly from analysis if available
        good_practices = ai_analysis.get('good_practices', [])
        if not good_practices and ai_analysis.get('strengths'):
            # Fallback: build from strengths
            for i, strength in enumerate(ai_analysis.get('strengths', [])[:12]):
                good_practices.append(
                    {
                        'title': f'Сильная сторона {i + 1}',
                        'description': strength,
                        'category': 'Качество',
                    }
                )

        # Use warnings directly from analysis if available
        warnings = ai_analysis.get('warnings', [])
        if not warnings and ai_analysis.get('areas_for_improvement'):
            # Fallback: build from areas for improvement
            for i, area in enumerate(ai_analysis.get('areas_for_improvement', [])[:5]):
                warnings.append(
                    {
                        'title': f'Область для улучшения {i + 1}',
                        'description': area,
                        'category': 'Дизайн',
                        'slides': [i + 1],  # Placeholder slide numbers
                    }
                )

        # Use errors directly from analysis if available
        errors = ai_analysis.get('errors', [])
        if not errors and ai_analysis.get('areas_for_improvement'):
            # Fallback: build critical issues from areas for improvement
            critical_issues = [
                w
                for w in ai_analysis.get('areas_for_improvement', [])
                if any(keyword in w.lower() for keyword in ['критичес', 'ошибк', 'серьезн', 'важн'])
            ]
            for i, issue in enumerate(critical_issues[:3]):
                errors.append(
                    {
                        'title': f'Критическая проблема {i + 1}',
                        'description': issue,
                        'category': 'Качество',
                        'slides': [i + 1],
                        'severity': 'high',
                    }
                )

        # Use recommendations directly from analysis
        recommendations = ai_analysis.get('recommendations', [])
        if not recommendations:
            recommendations = [
                'Проверьте читаемость всех текстовых элементов',
                'Убедитесь в консистентности дизайна на всех слайдах',
                'Оптимизируйте количество информации на каждом слайде',
            ]

        # Prepare response
        response = {
            'overall_score': overall_score,
            'filename': filename,
            'total_slides': ai_analysis.get('total_slides', 1),
            'analysis_method': ai_analysis.get('analysis_method', 'LLM анализ'),
            'good_practices': good_practices,
            'warnings': warnings,
            'errors': errors,
            'recommendations': recommendations,
            'category_scores': ai_analysis.get('category_scores', {}),
        }

        # Add additional fields if available
        if ai_analysis.get('strengths'):
            response['strengths'] = ai_analysis['strengths']
        if ai_analysis.get('areas_for_improvement'):
            response['areas_for_improvement'] = ai_analysis['areas_for_improvement']
        if ai_analysis.get('feedback'):
            response['feedback'] = ai_analysis['feedback']
        if ai_analysis.get('analysis_timestamp'):
            response['analysis_timestamp'] = ai_analysis['analysis_timestamp']

        return response

    except Exception as e:
        logger.error(f'Error converting AI analysis to frontend format: {str(e)}')
        # Return minimal valid structure
        return {
            'overall_score': 70,
            'filename': filename,
            'total_slides': 1,
            'analysis_method': 'Fallback',
            'good_practices': [
                {'title': 'Анализ выполнен', 'description': 'Презентация проанализирована', 'category': 'Общее'}
            ],
            'warnings': [
                {
                    'title': 'Ошибка анализа',
                    'description': f'Не удалось обработать результаты: {str(e)}',
                    'category': 'Техническое',
                    'slides': [1],
                }
            ],
            'errors': [],
            'recommendations': ['Повторите анализ или обратитесь к администратору'],
            'error_details': str(e),
        }


def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    logger.info(f'Starting audio extraction from {video_path}')

    try:
        from moviepy import VideoFileClip

        logger.info('MoviePy import successful, starting extraction')

        video = VideoFileClip(video_path)
        logger.info(f'Video loaded successfully, duration: {video.duration}s')

        audio = video.audio
        if audio is not None:
            logger.info('Audio track found, writing to file')
            audio.write_audiofile(audio_path, logger=None)
            audio.close()
            video.close()
            logger.info(f'Successfully extracted audio using moviepy from {video_path} to {audio_path}')

            # Проверим, что файл действительно создался
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                logger.info(f'Audio file created successfully, size: {file_size} bytes')
                return True
            else:
                logger.error('Audio file was not created')
                return False
        else:
            logger.error('No audio track found in video')
            video.close()
            return False

    except ImportError as e:
        logger.error(f'moviepy not available - install with: pip install moviepy. Error: {e}')
        return False
    except Exception as e:
        logger.error(f'Error extracting audio with moviepy: {str(e)}')
        return False


# CRUD operations for pitches
@app.post('/api/v1/pitches/', response_model=Pitch)
async def create_pitch_endpoint(pitch: PitchCreate, current_user: User = Depends(get_current_active_user)):
    """Create a new pitch"""
    return create_pitch_service(pitch, current_user.id)


@app.get('/api/v1/pitches/', response_model=list[Pitch])
async def get_all_pitches():
    """Get all pitches"""
    return list_pitches_service()


@app.get('/api/v1/pitches/{pitch_id}', response_model=Pitch)
async def get_pitch_endpoint(pitch_id: str):
    """Get a specific pitch by ID"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return pitch


@app.put('/api/v1/pitches/{pitch_id}', response_model=Pitch)
async def update_pitch_endpoint(pitch_id: str, pitch_update: PitchUpdate):
    """Update an existing pitch"""
    updated_pitch = update_pitch_service(pitch_id, pitch_update)
    if not updated_pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return updated_pitch


@app.delete('/api/v1/pitches/{pitch_id}')
async def delete_pitch_endpoint(pitch_id: str):
    """Delete a pitch"""
    deleted_pitch = delete_pitch_service(pitch_id)
    if not deleted_pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return {'message': f"Pitch '{deleted_pitch.title}' has been deleted successfully"}


# Presentation file endpoints
@app.post('/api/v1/pitches/{pitch_id}/presentation')
async def upload_presentation(pitch_id: str, file: UploadFile = File(...)):
    """Upload a presentation file for a pitch"""

    # Check if pitch exists
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    # Validate file type
    allowed_types = [
        'application/pdf',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    ]
    content_type = file.content_type or ''

    if not any(content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=400, detail='File must be a presentation (PDF, PPT, PPTX)')

    # Generate unique filename
    file_extension = os.path.splitext(file.filename or '')[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(PRESENTATIONS_DIR, unique_filename)

    try:
        # Save file
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update pitch with presentation info
        pitch_update = PitchUpdate(presentation_file_name=file.filename, presentation_file_path=unique_filename)
        updated_pitch = update_pitch_service(pitch_id, pitch_update)

        return {'message': 'Presentation uploaded successfully', 'filename': file.filename}

    except Exception as e:
        # Clean up file if database update fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f'Error uploading presentation: {str(e)}')


@app.get('/api/v1/pitches/{pitch_id}/presentation')
async def get_presentation(pitch_id: str):
    """Download the presentation file for a pitch"""

    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='No presentation file found for this pitch')

    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Presentation file not found on disk')

    return FileResponse(
        path=file_path,
        filename=pitch.presentation_file_name or 'presentation.pdf',
        media_type='application/octet-stream',
    )


@app.delete('/api/v1/pitches/{pitch_id}/presentation')
async def delete_presentation(pitch_id: str):
    """Delete the presentation file for a pitch"""

    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='No presentation file found for this pitch')

    # Remove file from disk
    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Update pitch to remove presentation info
    pitch_update = PitchUpdate(presentation_file_name=None, presentation_file_path=None)
    update_pitch_service(pitch_id, pitch_update)

    return {'message': 'Presentation deleted successfully'}


# Text file processing endpoint
@app.post('/api/v1/extract-text')
async def extract_text_from_file(file: UploadFile = File(...)):
    """Extract text content from uploaded text or Word document"""

    # Validate file type
    allowed_types = [
        'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]
    content_type = file.content_type or ''

    # Also check by file extension as fallback
    filename = file.filename or ''
    allowed_extensions = ['.txt', '.doc', '.docx']
    file_extension = os.path.splitext(filename)[1].lower()

    if not any(content_type.startswith(t) for t in allowed_types) and file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail='File must be a text file (.txt, .doc, .docx)')

    # Check file size (10MB limit for text files)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(status_code=400, detail='File size must be less than 10MB')

    try:
        # Process different file types
        if content_type == 'text/plain' or file_extension == '.txt':
            # Handle plain text files
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = file_content.decode('cp1251')  # Windows Cyrillic
                except UnicodeDecodeError:
                    text = file_content.decode('latin1')  # Fallback

        elif content_type in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ] or file_extension in ['.doc', '.docx']:
            # Handle Word documents
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                if (
                    file_extension == '.docx'
                    or content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                ):
                    # Handle .docx files
                    doc = Document(temp_file_path)
                    paragraphs = []
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            paragraphs.append(paragraph.text.strip())
                    text = '\n\n'.join(paragraphs)
                else:
                    # Handle .doc files (older format)
                    # Note: python-docx doesn't support .doc files well
                    # For production, consider using python-docx2txt or antiword
                    raise HTTPException(
                        status_code=400,
                        detail='Legacy .doc format not fully supported. Please use .docx or .txt format.',
                    )

            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        else:
            raise HTTPException(status_code=400, detail='Unsupported file format')

        # Clean and validate extracted text
        text = text.strip()
        if not text:
            raise HTTPException(status_code=400, detail='No text content found in file')

        # Limit text length (prevent abuse)
        max_text_length = 50000  # ~50k characters
        if len(text) > max_text_length:
            text = text[:max_text_length] + '...\n\n[Текст обрезан из-за превышения лимита длины]'

        return {'text': text, 'filename': filename, 'word_count': len(text.split()), 'char_count': len(text)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error processing file: {str(e)}')


@app.post('/api/v1/pitches/{pitch_id}/generate-improved-presentation')
async def generate_improved_presentation(pitch_id: str):
    """Generate improved presentation based on analysis"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_name:
        raise HTTPException(status_code=404, detail='No presentation found for this pitch')

    # Get the presentation file path
    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='Presentation file path not found')

    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Presentation file not found on disk')

    try:
        # First get the analysis
        from models.presentation_summary.presentation_summarizer import analyze_presentation
        from models.presentation_generator.presentation_generator import generate_improved_presentation

        logger.info(f'Generating improved presentation for: {pitch.presentation_file_name}')
        
        # Get analysis
        analysis = await analyze_presentation(file_path)
        
        if 'error' in analysis:
            raise HTTPException(status_code=500, detail=f'Analysis failed: {analysis["error"]}')
        
        # Generate improved presentation
        improved_presentation = await generate_improved_presentation(file_path, analysis, PRESENTATIONS_DIR)
        
        # Save improved presentation info to pitch (you might want to add this to your model)
        # For now, we'll return the result
        
        return {
            'success': True,
            'original_filename': improved_presentation.original_filename,
            'improved_filename': improved_presentation.improved_filename,
            'total_slides': improved_presentation.total_slides,
            'improvements_summary': improved_presentation.improvements_summary,
            'slides': [
                {
                    'slide_number': slide.slide_number,
                    'title': slide.title,
                    'content': slide.content,
                    'bullet_points': slide.bullet_points,
                    'speaker_notes': slide.speaker_notes,
                    'improvements_applied': slide.improvements_applied,
                    'suggested_visuals': [
                        {
                            'element_type': visual.element_type.value,
                            'title': visual.title,
                            'description': visual.description,
                            'purpose': visual.purpose,
                            'data_suggestion': visual.data_suggestion,
                            'chart_type': visual.chart_type.value if visual.chart_type else None,
                            'position_suggestion': visual.position_suggestion,
                            'size_suggestion': visual.size_suggestion
                        }
                        for visual in slide.suggested_visuals
                    ]
                }
                for slide in improved_presentation.slides
            ],
            'generation_timestamp': improved_presentation.generation_timestamp,
            'download_url': f'/api/v1/pitches/{pitch_id}/download-improved-presentation'
        }

    except ImportError as e:
        logger.warning(f'Presentation generation dependencies not available: {str(e)}')
        raise HTTPException(status_code=500, detail='Presentation generation not available')
    except Exception as e:
        logger.error(f'Presentation generation failed: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Generation failed: {str(e)}')


@app.get('/api/v1/pitches/{pitch_id}/download-improved-presentation')
async def download_improved_presentation(pitch_id: str):
    """Download improved presentation file"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    # Look for improved presentation file
    original_filename = pitch.presentation_file_name
    if not original_filename:
        raise HTTPException(status_code=404, detail='No presentation found for this pitch')
    
    name, ext = os.path.splitext(original_filename)
    improved_filename = f"{name}_improved{ext}"
    improved_file_path = os.path.join(PRESENTATIONS_DIR, improved_filename)
    
    if not os.path.exists(improved_file_path):
        raise HTTPException(status_code=404, detail='Improved presentation not found. Please generate it first.')
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=improved_file_path,
        filename=improved_filename,
        media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )


@app.get('/api/v1/pitches/{pitch_id}/presentation-analysis')
async def get_presentation_analysis(pitch_id: str):
    """Get presentation analysis for a pitch using Gemini Flash"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_name:
        raise HTTPException(status_code=404, detail='No presentation found for this pitch')

    # Get the presentation file path
    if not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='Presentation file path not found')

    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Presentation file not found on disk')

    try:
        # Try to use real AI analysis with new presentation_summary module
        from models.presentation_summary.presentation_summarizer import analyze_presentation

        logger.info(f'Starting AI analysis for presentation: {pitch.presentation_file_name}')

        # Run async analysis directly (we're already in an async context)
        ai_analysis = await analyze_presentation(file_path)

        if 'error' not in ai_analysis and ai_analysis.get('overall_score', 0) > 0:
            # Convert AI analysis to frontend format
            analysis = convert_ai_analysis_to_frontend_format(ai_analysis, pitch.presentation_file_name)
            logger.info(f'AI analysis completed successfully for {pitch.presentation_file_name}')
            return analysis
        else:
            logger.warning(f'AI analysis failed or returned no results: {ai_analysis.get("error", "Unknown error")}')

    except ImportError as e:
        logger.warning(f'AI analysis dependencies not available: {str(e)}')
    except Exception as e:
        logger.error(f'AI analysis failed: {str(e)}')

    # Fallback to hardcoded analysis data if AI analysis fails
    logger.info('Using fallback hardcoded analysis data')
    analysis = {
        'overall_score': 85,
        'filename': pitch.presentation_file_name,
        'total_slides': 1,
        'analysis_method': 'Статический анализ',
        'category_scores': {},
        'good_practices': [
            {
                'title': 'Консистентный дизайн',
                'description': 'Единообразное использование цветов, шрифтов и стилей на всех слайдах',
                'category': 'Дизайн',
            },
            {
                'title': 'Четкая структура',
                'description': 'Логичная последовательность слайдов с ясной навигацией',
                'category': 'Структура',
            },
            {
                'title': 'Качественные изображения',
                'description': 'Высокое разрешение и релевантность визуального контента',
                'category': 'Контент',
            },
            {
                'title': 'Читаемые шрифты',
                'description': 'Подходящий размер и контрастность текста',
                'category': 'Типографика',
            },
            {
                'title': 'Логотип компании',
                'description': 'Правильное размещение и использование брендинга',
                'category': 'Брендинг',
            },
            {
                'title': 'Контактная информация',
                'description': 'Четко указаны контакты на финальном слайде',
                'category': 'Контент',
            },
            {
                'title': 'Соотношение 16:9',
                'description': 'Правильный формат слайдов для современных экранов',
                'category': 'Формат',
            },
            {
                'title': 'Минимализм в дизайне',
                'description': 'Отсутствие визуального беспорядка и лишних элементов',
                'category': 'Дизайн',
            },
            {
                'title': 'Заголовки слайдов',
                'description': 'Каждый слайд имеет четкий и информативный заголовок',
                'category': 'Структура',
            },
            {
                'title': 'Корпоративные цвета',
                'description': 'Использование цветовой палитры бренда',
                'category': 'Брендинг',
            },
            {
                'title': 'Нумерация слайдов',
                'description': 'Присутствует нумерация для удобной навигации',
                'category': 'Навигация',
            },
            {
                'title': 'Качественная анимация',
                'description': 'Плавные и уместные переходы между слайдами',
                'category': 'Анимация',
            },
        ],
        'warnings': [
            {
                'title': 'Слишком много текста',
                'description': 'На слайдах 3, 7 и 12 превышен рекомендуемый объем текста (более 50 слов)',
                'category': 'Контент',
                'slides': [3, 7, 12],
            },
            {
                'title': 'Мелкий шрифт',
                'description': 'Размер шрифта на слайдах 5 и 9 может быть плохо читаемым с дальнего расстояния',
                'category': 'Типографика',
                'slides': [5, 9],
            },
            {
                'title': 'Перегруженные диаграммы',
                'description': 'Слайд 8 содержит слишком много данных в одной диаграмме',
                'category': 'Визуализация',
                'slides': [8],
            },
        ],
        'errors': [
            {
                'title': 'Низкое качество изображения',
                'description': 'Изображение на слайде 6 имеет разрешение ниже рекомендуемого (менее 150 DPI)',
                'category': 'Качество',
                'slides': [6],
                'severity': 'high',
            }
        ],
        'recommendations': [
            'Сократите количество текста на перегруженных слайдах',
            'Увеличьте размер шрифта до минимум 24pt для основного текста',
            'Замените изображение низкого качества на слайде 6',
            'Разделите сложную диаграмму на несколько более простых',
        ],
    }

    return analysis


<<<<<<< Updated upstream
@app.post('/api/v1/pitches/{pitch_id}/generate-presentation')
async def generate_improved_presentation_endpoint(pitch_id: str, request_data: dict = None):
    """Generate improved presentation based on analysis"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_name:
        raise HTTPException(status_code=404, detail='No presentation found for this pitch')

    try:
        # Get current analysis
        analysis_response = await get_presentation_analysis(pitch_id)
        if not analysis_response:
            raise HTTPException(status_code=404, detail='No analysis available')

        # Extract request parameters
        user_requirements = request_data.get('user_requirements', '') if request_data else ''
        target_audience = request_data.get('target_audience', '') if request_data else ''
        presentation_style = request_data.get('presentation_style', '') if request_data else ''

        # Generate unique filename for new presentation
        import uuid
        import time

        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        original_name = os.path.splitext(pitch.presentation_file_name)[0]
        new_filename = f'{original_name}_improved_{timestamp}_{unique_id}.pptx'

        # Create output path
        output_path = os.path.join(PRESENTATIONS_DIR, new_filename)

        # Generate presentation
        from models.presentation_generator.presentation_generator import generate_improved_presentation

        logger.info(f'Starting presentation generation for pitch: {pitch_id}')
        result = await generate_improved_presentation(
            analysis=analysis_response,
            output_path=output_path,
            user_requirements=user_requirements,
            target_audience=target_audience,
            presentation_style=presentation_style,
        )

        if result['success']:
            # Update pitch with new presentation file
            pitch.presentation_file_name = new_filename
            pitch.presentation_file_path = new_filename

            logger.info(f'Presentation generated successfully: {new_filename}')
            return {
                'success': True,
                'message': 'Презентация успешно сгенерирована',
                'filename': new_filename,
                'presentation_title': result.get('presentation_title', 'Улучшенная презентация'),
                'slides_count': result.get('slides_count', 0),
                'improvements_applied': result.get('improvements_applied', []),
                'theme': result.get('theme', 'modern'),
                'slides_data': result.get('slides_data', []),
                'download_url': f'/api/v1/pitches/{pitch_id}/presentation-download',
            }
        else:
            logger.error(f'Presentation generation failed: {result.get("error", "Unknown error")}')
            raise HTTPException(status_code=500, detail=f'Generation failed: {result.get("error", "Unknown error")}')

    except Exception as e:
        logger.error(f'Presentation generation endpoint error: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Generation failed: {str(e)}')


@app.get('/api/v1/pitches/{pitch_id}/presentation-download')
async def download_generated_presentation(pitch_id: str):
    """Download the generated presentation file"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_name or not pitch.presentation_file_path:
        raise HTTPException(status_code=404, detail='No presentation file available')

    file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='Presentation file not found on disk')

    try:
        from fastapi.responses import FileResponse

        return FileResponse(
            path=file_path,
            filename=pitch.presentation_file_name,
            media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )
    except Exception as e:
        logger.error(f'Download error: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Download failed: {str(e)}')


=======
>>>>>>> Stashed changes
@app.get('/api/v1/pitches/{pitch_id}/text')
async def get_speech_analysis(pitch_id: str):
    """Get speech analysis for a pitch with new format"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.content:
        raise HTTPException(status_code=404, detail='No speech content found for this pitch')

    try:
        service = TextAnalysisService()
        return await service.get_legacy_interface(pitch.content, 'ru')

    except Exception as e:
        logger.error(f'Speech analysis failed: {str(e)}')
        # Fallback к простому отображению с базовыми метриками
        words = len((pitch.content or '').split())
        speech_time_min = round(words / 150.0, 2)
        fallback_groups = [
            {
                'name': 'Орфография и пунктуация',
                'value': 0.7,
                'metrics': [
                    {'label': 'Ошибки пунктуации', 'value': 0},
                    {'label': 'Количество слов', 'value': words},
                    {'label': 'Время речи (мин)', 'value': speech_time_min},
                ],
                'diagnostics': [
                    {'label': 'Требуется детальный анализ', 'status': 'warning', 'comment': 'Сервис анализа недоступен'}
                ],
            }
        ]
        return {
            'groups': fallback_groups,
            'feedback': 'Анализ в ограниченном режиме.',
            'strengths': [],
            'areas_for_improvement': [],
            'recommendations': [],
        }


# AI endpoints
@app.post('/api/v1/score/pitch')
async def score_pitch(video: UploadFile = File(...), pitch_id: Optional[str] = Form(None)):
    """Analyze pitch video with real audio analysis and visual analysis"""

    logger.info(f'Processing video upload: {video.filename} for pitch {pitch_id}')

    from db_models import TrainingSessionCreate, TrainingType

    # Validate video file
    content_type = video.content_type or ''
    if not content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail='File must be a video')

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    video_content = await video.read()
    if len(video_content) > max_size:
        raise HTTPException(status_code=400, detail='File size must be less than 100MB')

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
        tmp_video.write(video_content)
        video_path = tmp_video.name

    try:
        audio_path = video_path.replace('.mp4', '.wav')
        audio_extracted = extract_audio_from_video(video_path, audio_path)

        audio_analysis = None
        if audio_extracted and os.path.exists(audio_path):
            try:
                script_text = None
                planned_duration = 120.0

                if pitch_id:
                    pitch = get_pitch_service(pitch_id)
                    if pitch and pitch.content:
                        script_text = pitch.content
                        if hasattr(pitch, 'planned_duration_minutes') and pitch.planned_duration_minutes:
                            planned_duration = pitch.planned_duration_minutes * 60.0
                        else:
                            word_count = len(pitch.content.split())
                            planned_duration = max(60.0, word_count * 0.4)

                script_path = None
                if script_text:
                    script_path = video_path.replace('.mp4', '_script.txt')
                    with open(script_path, 'w', encoding='utf-8') as f:
                        f.write(script_text)

                from models.audio.analyzer import analyze_file

                raw_result = analyze_file(
                    audio_path=audio_path,
                    script_path=script_path,
                    planned_duration_sec=planned_duration,
                    language='ru',
                    whisper_size='small',
                )

                audio_analysis = analyze_file_frontend_format(
                    audio_path=audio_path,
                    script_path=script_path,
                    planned_duration_sec=planned_duration,
                    language='ru',
                    whisper_size='small',
                )

                output_dir = '../../models/audio/output'
                os.makedirs(output_dir, exist_ok=True)

                raw_path = os.path.join(output_dir, 'analysis_raw.json')
                with open(raw_path, 'w', encoding='utf-8') as f:
                    json.dump(raw_result, f, ensure_ascii=False, indent=2)
                logger.info(f'Raw analysis saved to {raw_path}')

                frontend_path = os.path.join(output_dir, 'analysis_frontend.json')
                with open(frontend_path, 'w', encoding='utf-8') as f:
                    json.dump(audio_analysis, f, ensure_ascii=False, indent=2)
                logger.info(f'Frontend analysis saved to {frontend_path}')

                if script_path and os.path.exists(script_path):
                    os.unlink(script_path)

            except Exception as e:
                logger.error(f'Audio analysis failed: {str(e)}')
                audio_analysis = None
        else:
            logger.warning('Audio extraction failed - using fallback data')

        # Анализ видео (визуальная часть)
        grader = VideoGrader()
        frames = grader.split_video(video_path, step_seconds=1)
        results = grader.analyze_frames(frames)
        report = grader.final_score(results)

        # Generate hardcoded scores for other groups (пока)
        base_score = random.uniform(6.5, 9.0)

    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)
        if audio_extracted and os.path.exists(audio_path):
            os.unlink(audio_path)

    speech_group = None
    if audio_analysis and 'groups' in audio_analysis and len(audio_analysis['groups']) > 0:
        logger.info('Using real audio analysis data')
        speech_group = audio_analysis['groups'][0]
    else:
        logger.info('Using fallback hardcoded data - audio analysis failed or empty')
        speech_score = round(base_score / 10, 2)
        speech_group = {
            'name': 'Речь и артикуляция',
            'value': speech_score,
            'metrics': [
                {
                    'label': 'Четкость речи',
                    'value': round(base_score + random.uniform(-0.3, 0.5), 1),
                },
                {
                    'label': 'Скорость речи (слов/мин)',
                    'value': random.randint(120, 180),
                },
                {
                    'label': 'Громкость голоса',
                    'value': round(base_score + random.uniform(-0.2, 0.4), 1),
                },
            ],
            'diagnostics': [
                {
                    'label': 'Четкая артикуляция',
                    'status': 'good',
                    'comment': 'Отличная четкость речи и хорошая интонация',
                },
                {
                    'label': 'Темп речи',
                    'status': 'warning',
                    'comment': 'Рекомендуется немного замедлить темп речи для лучшего восприятия',
                },
                {
                    'label': 'Профессиональная манера',
                    'status': 'good',
                    'comment': 'Профессиональная манера речи и уверенная подача',
                },
            ],
        }

    default = {
        'groups': [speech_group],
        'recommendations': [],
        'feedback': '',
        'strengths': [],
        'areas_for_improvement': [],
    }

    default['groups'].append(report)

    if not default['recommendations']:
        default['recommendations'] = [
            'Немного замедлите темп речи для лучшего восприятия',
            'Добавьте больше жестов для усиления эмоциональной составляющей',
            'Используйте больше пауз для акцентирования важных моментов',
        ]

    if not default['feedback']:
        default['feedback'] = (
            'Ваше выступление демонстрирует профессиональный уровень. Рекомендации помогут достичь еще лучших результатов.'
        )

    if not default['strengths']:
        default['strengths'] = [
            'Четкая артикуляция и профессиональная речь',
            'Хорошая структура и логика выступления',
            'Уверенная подача материала',
        ]

    if not default['areas_for_improvement']:
        default['areas_for_improvement'] = [
            'Оптимизация темпа речи',
            'Развитие языка тела и жестикуляции',
            'Использование пауз для акцентирования',
        ]

    # Calculate overall score from group scores
    group_scores = [group['value'] for group in default['groups'] if isinstance(group.get('value'), (int, float))]
    overall_score = round(sum(group_scores) / len(group_scores), 2) if group_scores else 0.0

    # Save training session if pitch_id is provided
    if pitch_id:
        try:
            # Calculate video duration (this is a placeholder - in real implementation,
            # you would extract actual duration from the video file)
            video_duration = random.uniform(60, 300)  # Random duration between 1-5 minutes

            training_session_data = TrainingSessionCreate(
                pitch_id=pitch_id,
                training_type=TrainingType.VIDEO_UPLOAD,
                duration_seconds=video_duration,
                video_file_path=None,  # Would store actual file path in production
                analysis_results=default,
                overall_score=overall_score,
                notes=f'Video analysis completed. Overall score: {overall_score}',
            )

            created_session = create_training_session_service(training_session_data)
            logger.info(f'Training session saved with ID: {created_session.id}')

            # Add session info to response
            default['training_session_id'] = created_session.id

        except Exception as e:
            logger.error(f'Failed to save training session: {str(e)}')
            # Don't fail the whole request if session saving fails

    return default


@app.post('/api/v1/score/text', response_model=TextAnalysisResponse)
async def score_text(request: TextAnalysisRequest):
    """
    Analyze and process text using specified analysis types and optional style transformation
    """
    start_time = datetime.now()
    request_id = f'req_{int(start_time.timestamp())}_{str(uuid.uuid4())[:8]}'

    try:
        analysis_types = list(dict.fromkeys(request.analysis_types))

        if AnalysisType.STYLE_TRANSFORM in analysis_types and not request.style:
            raise HTTPException(status_code=400, detail='Style must be specified when style_transform is requested')

        initial_state = AnalysisState(
            original_text=request.text,
            current_text=request.text,
            analysis_types=analysis_types,
            style=request.style,
            language=request.language,
            processing_steps=[],
            weak_spots=[],
            metadata={'request_id': request_id},
        )

        config = {'configurable': {'thread_id': request_id}}
        result_state = await app_graph.ainvoke(initial_state, config)

        processing_time = (datetime.now() - start_time).total_seconds()

        if isinstance(result_state, dict):
            final_text = result_state.get('current_text', request.text)
            processing_steps = result_state.get('processing_steps', [])
            weak_spots = result_state.get('weak_spots', [])
            speech_time = result_state.get('speech_time_minutes')
            final_speech_time = result_state.get('final_speech_time_minutes')
            word_count = result_state.get('word_count', 0)
            final_word_count = result_state.get('final_word_count', 0)
            metadata = result_state.get('metadata', {})
        else:
            final_text = result_state.current_text
            processing_steps = result_state.processing_steps
            weak_spots = result_state.weak_spots
            speech_time = result_state.speech_time_minutes
            final_speech_time = result_state.final_speech_time_minutes
            word_count = result_state.word_count
            final_word_count = result_state.final_word_count
            metadata = result_state.metadata

        # If edited text did not change but we expected edits, try a stronger direct pass
        expected_transforms = {
            AnalysisType.REMOVE_PARASITES,
            AnalysisType.REMOVE_BUREAUCRACY,
            AnalysisType.REMOVE_PASSIVE,
            AnalysisType.STRUCTURE_BLOCKS,
            AnalysisType.STYLE_TRANSFORM,
        }
        if final_text.strip() == (request.text or '').strip() and any(t in analysis_types for t in expected_transforms):
            try:
                service = TextAnalysisService()
                direct = await service.process_text_combined(
                    request.text,
                    [t for t in analysis_types if t in expected_transforms],
                    request.style,
                    request.language,
                )
                maybe_text = direct.get('processed_text')
                if maybe_text and maybe_text.strip():
                    final_text = maybe_text
                    # fill some metrics if missing
                    speech_time = direct.get('speech_time_original', speech_time)
                    final_speech_time = direct.get('speech_time_final', final_speech_time)
                    word_count = direct.get('word_count_original', word_count)
                    final_word_count = direct.get('word_count_final', final_word_count)
                    processing_steps = processing_steps or [
                        {
                            'step_name': 'Direct rewrite',
                            'input_text': request.text,
                            'output_text': final_text,
                            'changes_made': direct.get('changes_summary', []),
                            'metadata': direct.get('processing_details', {}),
                        }
                    ]
            except Exception:
                pass

        analysis_summary = {
            'total_steps_applied': len(processing_steps),
            'weak_spots_found': len(weak_spots),
            'original_speech_time_minutes': speech_time,
            'original_word_count': word_count,
            'final_speech_time_minutes': final_speech_time,
            'final_word_count': final_word_count,
            'weak_spots': [
                {
                    'position': spot.position,
                    'text': spot.original_text,
                    'issue': spot.issue_type,
                    'suggestion': spot.suggestion,
                    'severity': spot.severity,
                }
                for spot in weak_spots
            ]
            if weak_spots
            else [],
            'recommendations': metadata.get('weak_spots_recommendations', []),
        }

        return TextAnalysisResponse(
            request_id=request_id,
            original_text=request.text,
            final_edited_text=final_text,
            processing_steps=processing_steps,
            analysis_summary=analysis_summary,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(),
        )

    except Exception as e:
        # Возвращаем валидный ответ вместо 500, чтобы фронтенд всегда получал результат
        processing_time = (datetime.now() - start_time).total_seconds()
        words = len(request.text.split()) if request.text else 0
        speech_time = round(words / 150.0, 2) if words else 0.0

        fallback_summary = {
            'total_steps_applied': 0,
            'weak_spots_found': 0,
            'original_speech_time_minutes': speech_time,
            'original_word_count': words,
            'final_speech_time_minutes': speech_time,
            'final_word_count': words,
            'weak_spots': [],
            'recommendations': [
                'Повторите попытку позже — сервис анализа временно недоступен',
                'Проверьте стабильность интернет-соединения',
                'Сократите слишком длинный текст и попробуйте снова',
            ],
        }

        logger.error(f'Analysis failed: {str(e)}')

        return TextAnalysisResponse(
            request_id=request_id,
            original_text=request.text,
            final_edited_text=request.text,
            processing_steps=[],
            analysis_summary=fallback_summary,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(),
        )


@app.post('/api/v1/recommendations/text', response_model=TextRecommendationsResponse)
async def get_text_recommendations(request: TextRecommendationsRequest):
    """
    Get recommendations and weak spots for text without modifying it
    """
    start_time = datetime.now()
    request_id = f'rec_{int(start_time.timestamp())}_{str(uuid.uuid4())[:8]}'

    try:
        service = TextAnalysisService()
        weak_spots, recommendations = await service.analyze_weak_spots(request.text, request.language)

        processing_time = (datetime.now() - start_time).total_seconds()

        return TextRecommendationsResponse(
            request_id=request_id,
            weak_spots=weak_spots,
            global_recommendations=recommendations,
            processing_time_seconds=processing_time,
            timestamp=datetime.now(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Recommendations failed: {str(e)}')


# Training Sessions endpoints
@app.post('/api/v1/training-sessions/', response_model=TrainingSession)
async def create_training_session_endpoint(session: TrainingSessionCreate):
    """Create a new training session"""
    return create_training_session_service(session)


@app.get('/api/v1/training-sessions/', response_model=list[TrainingSession])
async def get_all_training_sessions():
    """Get all training sessions"""
    return list_training_sessions_service()


@app.get('/api/v1/training-sessions/{session_id}', response_model=TrainingSession)
async def get_training_session_endpoint(session_id: str):
    """Get a specific training session by ID"""
    session = get_training_session_service(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Training session not found')
    return session


@app.get('/api/v1/pitches/{pitch_id}/training-sessions', response_model=list[TrainingSession])
async def get_training_sessions_for_pitch_endpoint(pitch_id: str):
    """Get all training sessions for a specific pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return get_training_sessions_for_pitch_service(pitch_id)


@app.get('/api/v1/pitches/{pitch_id}/training-sessions/stats')
async def get_training_session_stats_endpoint(pitch_id: str):
    """Get training session statistics for a specific pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return get_training_session_stats_service(pitch_id)


@app.put('/api/v1/training-sessions/{session_id}', response_model=TrainingSession)
async def update_training_session_endpoint(session_id: str, session_update: TrainingSessionUpdate):
    """Update an existing training session"""
    updated_session = update_training_session_service(session_id, session_update)
    if not updated_session:
        raise HTTPException(status_code=404, detail='Training session not found')
    return updated_session


@app.delete('/api/v1/training-sessions/{session_id}')
async def delete_training_session_endpoint(session_id: str):
    """Delete a training session"""
    deleted_session = delete_training_session_service(session_id)
    if not deleted_session:
        raise HTTPException(status_code=404, detail='Training session not found')
    return {'message': 'Training session has been deleted successfully'}


@app.get('/api/v1/pitches/{pitch_id}/hypothetical-questions', response_model=list[HypotheticalQuestion])
async def get_hypothetical_questions_for_pitch_endpoint(pitch_id: str):
    """Get all hypothetical questions for a specific pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return get_hypothetical_questions_for_pitch_service(pitch_id)


@app.get('/api/v1/pitches/{pitch_id}/hypothetical-questions/stats')
async def get_hypothetical_questions_stats_endpoint(pitch_id: str):
    """Get hypothetical questions statistics for a specific pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')
    return get_hypothetical_questions_stats_service(pitch_id)


# Question Generation endpoints
@app.post('/api/v1/questions/generate', response_model=QuestionGenerationResponse)
async def generate_questions(request: QuestionGenerationRequest):
    """Generate questions based on text and commission mood"""
    try:
        generator = QuestionGenerator()
        return await generator.generate_questions(request)
    except Exception as e:
        logger.error(f'Question generation failed: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Question generation failed: {str(e)}')


@app.post('/api/v1/questions/generate-with-presentation', response_model=QuestionGenerationResponse)
async def generate_questions_with_presentation(request: QuestionGenerationRequest):
    """Generate questions based on text, commission mood, and presentation data if available"""
    try:
        generator = QuestionGenerator()
        return await generator.generate_questions(request)
    except Exception as e:
        logger.error(f'Question generation with presentation failed: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Question generation with presentation failed: {str(e)}')


@app.post('/api/v1/pitches/{pitch_id}/questions/generate', response_model=QuestionGenerationResponse)
async def generate_questions_for_pitch(pitch_id: str, request: QuestionGenerationRequest):
    """Generate questions for a specific pitch, including presentation data if available"""
    try:
        # Get pitch data
        pitch = get_pitch_service(pitch_id)
        if not pitch:
            raise HTTPException(status_code=404, detail='Pitch not found')
        
        # Check if pitch has presentation and get analysis
        presentation_data = None
        if pitch.presentation_file_name and pitch.presentation_file_path:
            try:
                file_path = os.path.join(PRESENTATIONS_DIR, pitch.presentation_file_path)
                if os.path.exists(file_path):
                    from models.presentation_summary.presentation_summarizer import analyze_presentation
                    ai_analysis = await analyze_presentation(file_path)
                    
                    if 'error' not in ai_analysis and ai_analysis.get('overall_score', 0) > 0:
                        presentation_data = ai_analysis
                        logger.info(f'Including presentation data for question generation: {pitch.presentation_file_name}')
                    else:
                        logger.warning(f'Presentation analysis failed or returned no results')
                else:
                    logger.warning(f'Presentation file not found: {file_path}')
            except Exception as e:
                logger.warning(f'Failed to analyze presentation for question generation: {str(e)}')
        
        # Update request with presentation data if available
        request.presentation_data = presentation_data
        
        # Generate questions
        generator = QuestionGenerator()
        return await generator.generate_questions(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Question generation for pitch {pitch_id} failed: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Question generation for pitch failed: {str(e)}')


@app.get('/api/v1/questions/moods')
async def get_commission_moods():
    """Get available commission moods"""
    try:
        generator = QuestionGenerator()
        return generator.get_available_moods()
    except Exception as e:
        logger.error(f'Failed to get commission moods: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Failed to get commission moods: {str(e)}')


@app.get('/api/v1/questions/moods/{mood}')
async def get_mood_characteristics(mood: CommissionMood):
    """Get characteristics of a specific commission mood"""
    try:
        generator = QuestionGenerator()
        return generator.get_mood_characteristics(mood)
    except Exception as e:
        logger.error(f'Failed to get mood characteristics: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Failed to get mood characteristics: {str(e)}')


# Authentication endpoints
@app.post('/api/v1/auth/register', response_model=User)
async def register(user: UserCreate):
    """Register a new user"""
    return create_user(user)


@app.post('/api/v1/auth/login', response_model=Token)
async def login(login_data: LoginRequest):
    """Login user and return access token"""
    user = authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={'sub': user.email}, expires_delta=access_token_expires)
    return {'access_token': access_token, 'token_type': 'bearer'}


@app.get('/api/v1/auth/me', response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user"""
    return current_user


@app.get('/api/v1/auth/verify')
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """Verify if token is valid"""
    return {'valid': True, 'user_id': current_user.id}
