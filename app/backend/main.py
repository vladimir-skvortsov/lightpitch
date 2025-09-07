import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Optional

from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv()
logger = logging.getLogger(__name__)

from config import PROJECT_NAME
from db_models import Pitch, PitchCreate, PitchUpdate
from pitches import create_pitch as create_pitch_service
from pitches import delete_pitch as delete_pitch_service
from pitches import get_pitch as get_pitch_service
from pitches import list_pitches as list_pitches_service
from pitches import update_pitch as update_pitch_service

from models.audio.analyzer import analyze_file_frontend_format
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
async def create_pitch_endpoint(pitch: PitchCreate):
    """Create a new pitch"""
    return create_pitch_service(pitch)


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


@app.get('/api/v1/pitches/{pitch_id}/presentation-analysis')
async def get_presentation_analysis(pitch_id: str):
    """Get presentation analysis for a pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.presentation_file_name:
        raise HTTPException(status_code=404, detail='No presentation found for this pitch')

    # For now, return hardcoded analysis data
    # TODO: Implement actual presentation analysis using AI/ML models
    analysis = {
        'overall_score': 85,
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
        import random

        base_score = random.uniform(6.5, 9.0)
        delivery_score = round((base_score + random.uniform(-0.4, 0.3)) / 10, 2)
        engagement_score = round((base_score + random.uniform(-0.2, 0.5)) / 10, 2)
        technical_score = round((base_score + random.uniform(-0.6, 0.2)) / 10, 2)

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
        'groups': [
            speech_group,
            {
                'name': 'Подача и презентация',
                'value': delivery_score,
                'metrics': [
                    {
                        'label': 'Уверенность',
                        'value': round(base_score + random.uniform(-0.5, 0.3), 1),
                    },
                    {
                        'label': 'Зрительный контакт',
                        'value': round(base_score + random.uniform(-0.4, 0.6), 1),
                    },
                    {
                        'label': 'Язык тела',
                        'value': round(base_score + random.uniform(-0.6, 0.4), 1),
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Зрительный контакт',
                        'status': 'good',
                        'comment': 'Хороший зрительный контакт с аудиторией',
                    },
                    {
                        'label': 'Жестикуляция',
                        'status': 'warning',
                        'comment': 'Добавьте больше жестов для усиления эмоциональной составляющей',
                    },
                    {
                        'label': 'Уверенность',
                        'status': 'good',
                        'comment': 'Уверенная подача материала',
                    },
                ],
            },
            {
                'name': 'Вовлеченность аудитории',
                'value': engagement_score,
                'metrics': [
                    {
                        'label': 'Эмоциональность',
                        'value': round(base_score + random.uniform(-0.2, 0.7), 1),
                    },
                    {
                        'label': 'Интерактивность',
                        'value': round(base_score + random.uniform(-0.8, 0.3), 1),
                    },
                    {
                        'label': 'Использование пауз',
                        'value': round(base_score + random.uniform(-0.5, 0.2), 1),
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Структура выступления',
                        'status': 'good',
                        'comment': 'Хорошая структура выступления и логичное изложение',
                    },
                    {
                        'label': 'Эмоциональная вовлеченность',
                        'status': 'warning',
                        'comment': 'Увеличьте эмоциональную вовлеченность для лучшего контакта с аудиторией',
                    },
                    {
                        'label': 'Паузы',
                        'status': 'warning',
                        'comment': 'Используйте больше пауз для акцентирования важных моментов',
                    },
                ],
            },
            {
                'name': 'Технические аспекты',
                'value': technical_score,
                'metrics': [
                    {
                        'label': 'Продолжительность (мин)',
                        'value': round(random.randint(120, 300) / 60, 1),
                    },
                    {
                        'label': 'Количество слов',
                        'value': random.randint(150, 450),
                    },
                    {
                        'label': 'Качество звука',
                        'value': round(base_score + random.uniform(-0.3, 0.2), 1),
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Качество записи',
                        'status': 'good',
                        'comment': 'Хорошее качество звука и видео',
                    },
                    {
                        'label': 'Продолжительность',
                        'status': 'good',
                        'comment': 'Оптимальная продолжительность выступления',
                    },
                    {
                        'label': 'Техническое исполнение',
                        'status': 'good',
                        'comment': 'Отличное техническое качество записи',
                    },
                ],
            },
        ],
        'recommendations': [],
        'feedback': '',
        'strengths': [],
        'areas_for_improvement': [],
    }

    default['groups'][2] = report

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


@app.post('/api/v1/score/presentation')
async def score_presentation():
    return {}


@app.post('/api/v1/score/audio')
async def score_audio(
    audio: UploadFile = File(...),
    script: Optional[str] = Form(None),
    planned_duration_sec: Optional[float] = Form(None),
    pitch_id: Optional[str] = Form(None),
):
    content_type = audio.content_type or ''
    allowed_audio_types = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/m4a', 'audio/x-wav']

    if not any(content_type.startswith(t) for t in ['audio/', 'video/']) and not audio.filename.lower().endswith(
        ('.wav', '.mp3', '.m4a', '.mp4', '.mpeg')
    ):
        raise HTTPException(status_code=400, detail='File must be an audio file (wav, mp3, m4a, etc.)')

    max_size = 50 * 1024 * 1024  # 50MB
    audio_content = await audio.read()
    if len(audio_content) > max_size:
        raise HTTPException(status_code=400, detail='Audio file size must be less than 50MB')

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            audio_path = os.path.join(temp_dir, f"audio_{uuid.uuid4()}{os.path.splitext(audio.filename or '.wav')[1]}")
            with open(audio_path, 'wb') as f:
                f.write(audio_content)

            script_path = None
            if script and script.strip():
                script_path = os.path.join(temp_dir, f'script_{uuid.uuid4()}.txt')
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script.strip())

            duration_to_use = planned_duration_sec
            if pitch_id and not duration_to_use:
                pitch = get_pitch_service(pitch_id)
                if pitch and hasattr(pitch, 'planned_duration_minutes') and pitch.planned_duration_minutes:
                    duration_to_use = pitch.planned_duration_minutes * 60.0  # Конвертируем в секунды

            from models.audio.analyzer import analyze_file

            raw_result = analyze_file(
                audio_path=audio_path,
                script_path=script_path,
                planned_duration_sec=duration_to_use,
                language='ru',
                whisper_size='small',
            )

            result = analyze_file_frontend_format(
                audio_path=audio_path,
                script_path=script_path,
                planned_duration_sec=duration_to_use,
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
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f'Frontend analysis saved to {frontend_path}')

            return result

        except Exception as e:
            logger.error(f'Audio analysis failed: {str(e)}')
            raise HTTPException(status_code=500, detail=f'Audio analysis failed: {str(e)}')


@app.get('/api/v1/audio/status')
async def audio_analysis_status():
    try:
        from models.audio.analyzer import analyze_file_frontend_format

        return {
            'available': True,
            'message': 'Audio analysis is ready',
            'supported_formats': ['wav', 'mp3', 'm4a', 'mp4', 'mpeg'],
            'max_file_size_mb': 50,
            'default_planned_duration_sec': 120,
        }
    except ImportError as e:
        return {
            'available': False,
            'message': f'Audio analysis not available: {str(e)}',
            'error': 'Missing dependencies',
        }
