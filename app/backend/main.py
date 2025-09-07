import os
import shutil
import tempfile
import uuid
from typing import Optional

from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime

load_dotenv()

from config import PROJECT_NAME
from db_models import Pitch, PitchCreate, PitchUpdate
from pitches import create_pitch as create_pitch_service
from pitches import delete_pitch as delete_pitch_service
from pitches import get_pitch as get_pitch_service
from pitches import list_pitches as list_pitches_service
from pitches import update_pitch as update_pitch_service
from models.text_editor.text_analysis import (
    TextAnalysisResponse,
    TextAnalysisRequest,
    TextRecommendationsResponse,
    TextRecommendationsRequest,
    AnalysisState,
    AnalysisType,
    TextAnalysisService,
    app_graph,
)

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

    # For now, return hardcoded analysis data in new group-based format
    # TODO: Implement actual presentation analysis using AI/ML models
    analysis = {
        'groups': [
            {
                'name': 'Дизайн и визуализация',
                'value': 0.88,
                'metrics': [
                    {
                        'label': 'Цветовая схема',
                        'value': 9.2,
                    },
                    {
                        'label': 'Качество изображений',
                        'value': 7.8,
                    },
                    {
                        'label': 'Визуальная консистентность',
                        'value': 9.5,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Консистентный дизайн',
                        'status': 'good',
                        'comment': 'Единообразное использование цветов, шрифтов и стилей на всех слайдах',
                    },
                    {
                        'label': 'Качественные изображения',
                        'status': 'good',
                        'comment': 'Высокое разрешение и релевантность визуального контента',
                    },
                    {
                        'label': 'Минимализм в дизайне',
                        'status': 'good',
                        'comment': 'Отсутствие визуального беспорядка и лишних элементов',
                    },
                    {
                        'label': 'Низкое качество изображения',
                        'status': 'error',
                        'sublabel': 'Слайд 6',
                        'comment': 'Изображение имеет разрешение ниже рекомендуемого (менее 150 DPI)',
                    },
                ],
            },
            {
                'name': 'Структура и навигация',
                'value': 0.92,
                'metrics': [
                    {
                        'label': 'Количество слайдов',
                        'value': 15,
                    },
                    {
                        'label': 'Логическая последовательность',
                        'value': 9.3,
                    },
                    {
                        'label': 'Навигационные элементы',
                        'value': 8.8,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Четкая структура',
                        'status': 'good',
                        'comment': 'Логичная последовательность слайдов с ясной навигацией',
                    },
                    {
                        'label': 'Заголовки слайдов',
                        'status': 'good',
                        'comment': 'Каждый слайд имеет четкий и информативный заголовок',
                    },
                    {
                        'label': 'Нумерация слайдов',
                        'status': 'good',
                        'comment': 'Присутствует нумерация для удобной навигации',
                    },
                ],
            },
            {
                'name': 'Типографика и контент',
                'value': 0.74,
                'metrics': [
                    {
                        'label': 'Размер шрифта',
                        'value': 22,
                    },
                    {
                        'label': 'Количество слов на слайд',
                        'value': 45,
                    },
                    {
                        'label': 'Читаемость',
                        'value': 8.1,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Читаемые шрифты',
                        'status': 'good',
                        'comment': 'Подходящий размер и контрастность текста',
                    },
                    {
                        'label': 'Слишком много текста',
                        'status': 'warning',
                        'sublabel': 'Слайды 3, 7, 12',
                        'comment': 'Превышен рекомендуемый объем текста (более 50 слов)',
                    },
                    {
                        'label': 'Мелкий шрифт',
                        'status': 'warning',
                        'sublabel': 'Слайды 5, 9',
                        'comment': 'Размер шрифта может быть плохо читаемым с дальнего расстояния',
                    },
                ],
            },
            {
                'name': 'Брендинг и оформление',
                'value': 0.95,
                'metrics': [
                    {
                        'label': 'Соответствие бренду',
                        'value': 9.7,
                    },
                    {
                        'label': 'Логотип и контакты',
                        'value': 10,
                    },
                    {
                        'label': 'Цветовая палитра',
                        'value': 9.2,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Логотип компании',
                        'status': 'good',
                        'comment': 'Правильное размещение и использование брендинга',
                    },
                    {
                        'label': 'Корпоративные цвета',
                        'status': 'good',
                        'comment': 'Использование цветовой палитры бренда',
                    },
                    {
                        'label': 'Контактная информация',
                        'status': 'good',
                        'comment': 'Четко указаны контакты на финальном слайде',
                    },
                    {
                        'label': 'Соотношение 16:9',
                        'status': 'good',
                        'comment': 'Правильный формат слайдов для современных экранов',
                    },
                ],
            },
        ],
        'recommendations': [
            'Сократите количество текста на перегруженных слайдах до 30-40 слов',
            'Увеличьте размер шрифта до минимум 24pt для основного текста',
            'Замените изображение низкого качества на слайде 6 на версию высокого разрешения',
            'Разделите сложную диаграмму на несколько более простых',
            'Добавьте больше визуальных элементов для поддержки текста',
            'Используйте единообразные отступы и выравнивание на всех слайдах',
        ],
        'feedback': 'Ваша презентация демонстрирует отличное соответствие бренду и хорошую структуру. Основные области для улучшения: оптимизация текстового контента и качества изображений.',
        'strengths': [
            'Отличное соответствие корпоративному стилю',
            'Четкая логическая структура презентации',
            'Качественное оформление и навигация',
            'Правильное использование брендинга',
            'Хорошая визуальная консистентность',
        ],
        'areas_for_improvement': [
            'Оптимизация объема текста на слайдах',
            'Улучшение качества изображений',
            'Увеличение размера шрифта для лучшей читаемости',
            'Упрощение сложных диаграмм',
            'Балансировка текста и визуальных элементов',
        ],
    }

    return analysis


@app.get('/api/v1/pitches/{pitch_id}/text')
async def get_speech_analysis(pitch_id: str):
    """Get speech analysis for a pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.content:
        raise HTTPException(status_code=404, detail='No speech content found for this pitch')

    # For now, return hardcoded analysis data in new format
    # TODO: Implement actual speech analysis using AI/ML models
    analysis = {
        'groups': [
            {
                'name': 'Структура',
                'value': 0.85,
                'metrics': [
                    {
                        'label': 'Количество разделов',
                        'value': 4,
                    },
                    {
                        'label': 'Логическая последовательность',
                        'value': 8.5,
                    },
                    {
                        'label': 'Переходы между разделами',
                        'value': 7.2,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Четкое введение',
                        'status': 'good',
                        'comment': 'Выступление имеет ясное и структурированное введение',
                    },
                    {
                        'label': 'Основная часть',
                        'status': 'good',
                        'comment': 'Логично построенная аргументация с примерами',
                    },
                    {
                        'label': 'Заключение',
                        'status': 'warning',
                        'sublabel': 'Слабое резюме',
                        'comment': 'Заключение не подводит итоги основных моментов',
                    },
                    {
                        'label': 'Переходы',
                        'status': 'warning',
                        'sublabel': '2 отсутствующих перехода',
                        'comment': 'Между разделами 3-4 и 5-6 отсутствуют плавные переходы',
                    },
                ],
            },
            {
                'name': 'Содержание',
                'value': 0.78,
                'metrics': [
                    {
                        'label': 'Релевантность темы',
                        'value': 9.1,
                    },
                    {
                        'label': 'Количество примеров',
                        'value': 6,
                    },
                    {
                        'label': 'Глубина проработки',
                        'value': 7.8,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Актуальность',
                        'status': 'good',
                        'comment': 'Затрагиваются актуальные для аудитории вопросы',
                    },
                    {
                        'label': 'Конкретные примеры',
                        'status': 'good',
                        'comment': 'Приводятся релевантные примеры для иллюстрации',
                    },
                    {
                        'label': 'Статистические данные',
                        'status': 'error',
                        'sublabel': 'Отсутствуют в 3 разделах',
                        'comment': 'Утверждения не подкреплены числовыми данными',
                    },
                    {
                        'label': 'Призыв к действию',
                        'status': 'good',
                        'comment': 'Четко сформулировано, что должна делать аудитория',
                    },
                ],
            },
            {
                'name': 'Стиль и язык',
                'value': 0.63,
                'metrics': [
                    {
                        'label': 'Средняя длина предложения',
                        'value': 18.5,
                    },
                    {
                        'label': 'Разнообразие лексики',
                        'value': 6.8,
                    },
                    {
                        'label': 'Читаемость текста',
                        'value': 7.5,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Краткость изложения',
                        'status': 'good',
                        'comment': 'Основные идеи представлены четко и ясно',
                    },
                    {
                        'label': 'Длина предложений',
                        'status': 'warning',
                        'sublabel': '8 слишком длинных',
                        'comment': 'Некоторые предложения превышают 25 слов',
                    },
                    {
                        'label': 'Повторы слов',
                        'status': 'warning',
                        'sublabel': 'Слово "инновация" 12 раз',
                        'comment': 'Частое повторение ключевых терминов',
                    },
                    {
                        'label': 'Сложная терминология',
                        'status': 'warning',
                        'sublabel': '5 необъясненных терминов',
                        'comment': 'Специальные термины без разъяснений',
                    },
                ],
            },
            {
                'name': 'Эмоциональное воздействие',
                'value': 0.72,
                'metrics': [
                    {
                        'label': 'Эмоциональная насыщенность',
                        'value': 7.8,
                    },
                    {
                        'label': 'Убедительность',
                        'value': 8.2,
                    },
                    {
                        'label': 'Вовлеченность аудитории',
                        'value': 6.5,
                    },
                ],
                'diagnostics': [
                    {
                        'label': 'Эмоциональная связь',
                        'status': 'good',
                        'comment': 'Используются элементы для вовлечения аудитории',
                    },
                    {
                        'label': 'Убедительные аргументы',
                        'status': 'good',
                        'comment': 'Приводятся веские доводы в поддержку тезисов',
                    },
                    {
                        'label': 'Интерактивность',
                        'status': 'warning',
                        'sublabel': 'Мало вопросов к аудитории',
                        'comment': 'Недостаточное взаимодействие с аудиторией',
                    },
                ],
            },
        ],
        'recommendations': [
            'Сократите длинные предложения до 20-25 слов для лучшего восприятия',
            'Добавьте конкретную статистику в разделы 2, 4 и 6',
            'Улучшите заключение, добавив краткое резюме ключевых моментов',
            'Добавьте переходные фразы между разделами 3-4 и 5-6',
            'Объясните специальные термины или замените их на простые аналоги',
            'Разнообразьте лексику, используйте синонимы для часто повторяющихся слов',
            'Добавьте больше вопросов к аудитории для повышения вовлеченности',
        ],
        'feedback': 'Ваше выступление демонстрирует хорошую структуру и актуальное содержание. Основные области для улучшения: упрощение языка и добавление статистических данных.',
        'strengths': [
            'Четкая логическая структура выступления',
            'Актуальная и релевантная тематика',
            'Хорошие примеры и иллюстрации',
            'Убедительная аргументация',
            'Эмоциональное воздействие на аудиторию',
        ],
        'areas_for_improvement': [
            'Сокращение длины предложений',
            'Добавление статистических данных',
            'Улучшение переходов между разделами',
            'Упрощение сложной терминологии',
            'Повышение интерактивности с аудиторией',
        ],
    }

    return analysis


# AI endpoints
@app.post('/api/v1/score/pitch')
async def score_pitch(video: UploadFile = File(...), pitch_id: Optional[str] = Form(None)):
    """Analyze pitch video and return hardcoded results"""

    # Validate video file
    content_type = video.content_type or ''
    if not content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail='File must be a video')

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    video_content = await video.read()
    if len(video_content) > max_size:
        raise HTTPException(status_code=400, detail='File size must be less than 100MB')

    # TODO: Интеграция с AI для анализа видео
    # Пока возвращаем hardcoded результаты

    import random
    import time

    time.sleep(1)

    base_score = random.uniform(6.5, 9.0)

    # Generate group scores
    speech_score = round(base_score / 10, 2)
    delivery_score = round((base_score + random.uniform(-0.4, 0.3)) / 10, 2)
    engagement_score = round((base_score + random.uniform(-0.2, 0.5)) / 10, 2)
    technical_score = round((base_score + random.uniform(-0.6, 0.2)) / 10, 2)

    return {
        'groups': [
            {
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
            },
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
        'recommendations': [
            'Немного замедлите темп речи для лучшего восприятия',
            'Добавьте больше жестов для усиления эмоциональной составляющей',
            'Используйте больше пауз для акцентирования важных моментов',
            'Увеличьте эмоциональную вовлеченность с аудиторией',
            'Поддерживайте зрительный контакт на протяжении всего выступления',
            'Работайте над вариативностью интонации',
        ],
        'feedback': 'Ваше выступление демонстрирует высокий профессиональный уровень с четкой артикуляцией и уверенной подачей. Основные области для улучшения: темп речи и эмоциональная вовлеченность.',
        'strengths': [
            'Четкая артикуляция и профессиональная речь',
            'Хорошая структура и логика выступления',
            'Уверенная подача материала',
            'Качественный зрительный контакт с аудиторией',
            'Отличное техническое исполнение',
        ],
        'areas_for_improvement': [
            'Оптимизация темпа речи',
            'Развитие языка тела и жестикуляции',
            'Использование пауз для акцентирования',
            'Повышение эмоциональной вовлеченности',
            'Увеличение интерактивности с аудиторией',
        ],
    }


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
        raise HTTPException(status_code=500, detail=f'Analysis failed: {str(e)}')


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
