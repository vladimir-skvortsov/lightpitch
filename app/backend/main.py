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

load_dotenv()

from config import PROJECT_NAME
from db_models import Pitch, PitchCreate, PitchUpdate
from pitches import create_pitch as create_pitch_service
from pitches import delete_pitch as delete_pitch_service
from pitches import get_pitch as get_pitch_service
from pitches import list_pitches as list_pitches_service
from pitches import update_pitch as update_pitch_service

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
    """Get speech analysis for a pitch"""
    pitch = get_pitch_service(pitch_id)
    if not pitch:
        raise HTTPException(status_code=404, detail='Pitch not found')

    if not pitch.content:
        raise HTTPException(status_code=404, detail='No speech content found for this pitch')

    # For now, return hardcoded analysis data
    # TODO: Implement actual speech analysis using AI/ML models
    analysis = {
        'overall_score': 72,
        'good_practices': [
            {
                'title': 'Четкая структура выступления',
                'description': 'Выступление имеет логичное введение, основную часть и заключение',
                'category': 'Структура',
            },
            {
                'title': 'Использование конкретных примеров',
                'description': 'Приводятся релевантные примеры для иллюстрации ключевых точек',
                'category': 'Содержание',
            },
            {
                'title': 'Призыв к действию',
                'description': 'В заключении четко сформулировано, что должна делать аудитория',
                'category': 'Заключение',
            },
            {
                'title': 'Эмоциональная связь',
                'description': 'Используются эмоциональные элементы для вовлечения аудитории',
                'category': 'Воздействие',
            },
            {
                'title': 'Краткость изложения',
                'description': 'Основные идеи представлены кратко и ясно',
                'category': 'Стиль',
            },
            {
                'title': 'Актуальная проблематика',
                'description': 'Затрагиваются актуальные для аудитории вопросы',
                'category': 'Релевантность',
            },
            {
                'title': 'Логическая последовательность',
                'description': 'Идеи представлены в логической последовательности',
                'category': 'Структура',
            },
            {
                'title': 'Убедительные аргументы',
                'description': 'Приводятся веские аргументы в поддержку основных тезисов',
                'category': 'Аргументация',
            },
        ],
        'warnings': [
            {
                'title': 'Длинные предложения',
                'description': 'Некоторые предложения слишком длинные и могут быть трудными для восприятия',
                'category': 'Стиль',
                'position': 'Абзацы 2, 5',
            },
            {
                'title': 'Повторы слов',
                'description': 'Слово "инновация" повторяется слишком часто',
                'category': 'Лексика',
                'position': 'По всему тексту',
            },
            {
                'title': 'Недостаток переходов',
                'description': 'Между некоторыми разделами отсутствуют плавные переходы',
                'category': 'Структура',
                'position': 'Абзацы 3-4',
            },
            {
                'title': 'Сложная терминология',
                'description': 'Используется специальная терминология без объяснений',
                'category': 'Понятность',
                'position': 'Абзац 6',
            },
            {
                'title': 'Отсутствие статистики',
                'description': 'Утверждения не подкреплены числовыми данными',
                'category': 'Доказательность',
                'position': 'Абзацы 4, 7',
            },
        ],
        'errors': [
            {
                'title': 'Нечеткое введение',
                'description': 'Во введении не ясно сформулирована цель выступления',
                'category': 'Структура',
                'position': 'Абзац 1',
                'severity': 'high',
            },
            {
                'title': 'Слабое заключение',
                'description': 'Заключение не резюмирует ключевые моменты выступления',
                'category': 'Заключение',
                'position': 'Последний абзац',
                'severity': 'medium',
            },
        ],
        'recommendations': [
            'Сократите длинные предложения для лучшего восприятия',
            'Добавьте конкретную статистику для подтверждения утверждений',
            'Четче сформулируйте цель выступления во введении',
            'Улучшите заключение, резюмируя ключевые моменты',
            'Добавьте переходные фразы между разделами',
            'Объясните специальную терминологию для широкой аудитории',
            'Разнообразьте лексику, избегая частых повторов',
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

    return {
        'overall_score': round(base_score, 1),
        'confidence': round(base_score + random.uniform(-0.5, 0.3), 1),
        'clarity': round(base_score + random.uniform(-0.3, 0.5), 1),
        'pace': round(base_score + random.uniform(-0.8, 0.2), 1),
        'engagement': round(base_score + random.uniform(-0.2, 0.7), 1),
        'body_language': round(base_score + random.uniform(-0.6, 0.4), 1),
        'eye_contact': round(base_score + random.uniform(-0.4, 0.6), 1),
        'voice_tone': round(base_score + random.uniform(-0.3, 0.4), 1),
        'duration': f'{random.randint(1, 5)}:{random.randint(10, 59):02d}',
        'word_count': random.randint(150, 450),
        'feedback': [
            {
                'type': 'positive',
                'message': random.choice(
                    [
                        'Отличная четкость речи и хорошая интонация',
                        'Уверенная подача материала',
                        'Хороший зрительный контакт с аудиторией',
                        'Профессиональная манера речи',
                    ]
                ),
            },
            {
                'type': 'improvement',
                'message': random.choice(
                    [
                        'Рекомендуется немного замедлить темп речи для лучшего восприятия',
                        'Добавьте больше жестов для усиления эмоциональной составляющей',
                        'Используйте больше пауз для акцентирования важных моментов',
                        'Увеличьте эмоциональную вовлеченность',
                    ]
                ),
            },
            {
                'type': 'positive',
                'message': random.choice(
                    ['Хорошая структура выступления', 'Логичное изложение материала', 'Удачные примеры и аналогии']
                ),
            },
        ],
        'strengths': [
            'Четкая артикуляция',
            'Хорошая структура выступления',
            'Уверенная подача материала',
            'Профессиональная манера речи',
        ],
        'areas_for_improvement': [
            'Темп речи',
            'Язык тела и жестикуляция',
            'Паузы для акцентирования',
            'Эмоциональная вовлеченность',
        ],
    }


@app.post('/api/v1/score/presentation')
async def score_presentation():
    return {}
